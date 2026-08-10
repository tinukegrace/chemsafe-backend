import uuid

from django.conf import settings
from django.db import models

from apps.inventory.models import Chemical, HazardClass

SEVERITY_CHOICES = [("critical", "Critical"), ("high", "High"), ("medium", "Medium")]
SEVERITY_LEVEL_BY_LABEL = {"critical": 3, "high": 2, "medium": 1}


class IncompatibilityRule(models.Model):
    """A documented, DB-stored chemical storage incompatibility rule.

    Every field here maps directly to a row in RULE_SET.md — the rule set is
    data, not code, so it stays maintainable/explainable without a deploy.
    See RULE_SET.md for the full rationale and source citations behind each
    seeded rule (apps/hazards/management/commands/seed_hazard_rules.py).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hazard_class_a = models.CharField(max_length=20, choices=HazardClass.choices)
    hazard_class_b = models.CharField(max_length=20, choices=HazardClass.choices)

    principle = models.CharField(
        max_length=100, default="", blank=True,
        help_text="Short named principle, e.g. 'Oxidizer–flammable segregation'.",
    )
    description = models.CharField(
        max_length=255, default="", blank=True,
        help_text="Plain-language summary of what this rule detects.",
    )
    reason = models.TextField(
        default="", blank=True,
        help_text="The safety mechanism: why this pairing is dangerous.",
    )
    recommended_action = models.TextField(
        default="", blank=True,
        help_text="Concrete corrective action for laboratory personnel.",
    )
    reference_source = models.CharField(
        max_length=255, default="", blank=True,
        help_text="General guidance this rule is drawn from (e.g. OSHA/NFPA/NOAA/Flinn).",
    )

    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="high")
    severity_level = models.PositiveSmallIntegerField(
        default=1, help_text="Numeric counterpart to severity (critical=3, high=2, medium=1).",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hazard_class_a", "hazard_class_b"], name="unique_hazard_pair")
        ]

    def __str__(self):
        return f"{self.principle or f'{self.hazard_class_a} + {self.hazard_class_b}'}"

    def save(self, *args, **kwargs):
        # Keep the numeric level consistent with the categorical label —
        # both are stored (not just derived) so the alert snapshot below can
        # copy a single source of truth at detection time.
        self.severity_level = SEVERITY_LEVEL_BY_LABEL.get(self.severity, self.severity_level)
        super().save(*args, **kwargs)


class IncompatibilityAlert(models.Model):
    """A detected violation of an IncompatibilityRule between two co-located
    chemicals. Rule content is snapshotted at detection time (principle,
    reason, severity, recommended_action) so the alert remains fully
    self-explaining even if the rule is later edited or removed — the same
    pattern used for ChemicalAuditLog.chemical_name.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(
        IncompatibilityRule, null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )

    chemical_a = models.ForeignKey(
        Chemical, null=True, blank=True, on_delete=models.SET_NULL, related_name="incompatibility_alerts_as_a"
    )
    chemical_a_name = models.CharField(max_length=255)
    chemical_a_hazard_class = models.CharField(max_length=20, choices=HazardClass.choices)

    chemical_b = models.ForeignKey(
        Chemical, null=True, blank=True, on_delete=models.SET_NULL, related_name="incompatibility_alerts_as_b"
    )
    chemical_b_name = models.CharField(max_length=255)
    chemical_b_hazard_class = models.CharField(max_length=20, choices=HazardClass.choices)

    location = models.CharField(max_length=255)

    # Snapshot of the matched rule at detection time — see class docstring.
    principle = models.CharField(max_length=100)
    reason = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    severity_level = models.PositiveSmallIntegerField()
    recommended_action = models.TextField()

    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="resolved_incompatibility_alerts",
    )
    archived = models.BooleanField(default=False)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-severity_level", "-detected_at"]
        constraints = [
            models.UniqueConstraint(fields=["chemical_a", "chemical_b", "rule"], name="unique_active_incompatibility")
        ]

    def __str__(self):
        return f"{self.principle}: {self.chemical_a_name} + {self.chemical_b_name} @ {self.location}"

    @property
    def status(self) -> str:
        if self.archived:
            return "archived"
        if self.resolved:
            return "resolved"
        return "open"
