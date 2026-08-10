import uuid

from django.conf import settings
from django.db import models

from apps.inventory.models import Chemical


class AlertType(models.TextChoices):
    EXPIRED = "expired", "Expired"
    NEAR_EXPIRY = "near_expiry", "Near expiry"
    LOW_STOCK = "low_stock", "Low stock"
    HAZARD = "hazard", "Hazard"
    # Storage-incompatibility findings are NOT modeled here — they need two
    # chemicals plus a linked rule, which doesn't fit this single-chemical
    # shape. See hazards.IncompatibilityAlert instead.


class Alert(models.Model):
    """Persisted alert, replacing the old client-only in-memory alert feed.

    Populated/refreshed by the `refresh_alerts` management command (Phase 4);
    resolve/archive actions here are real and survive a reload.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chemical = models.ForeignKey(Chemical, on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    message = models.CharField(max_length=500)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_alerts"
    )
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["chemical", "alert_type"], name="unique_active_alert_per_type")
        ]

    def __str__(self):
        return f"{self.alert_type} for {self.chemical_id}"
