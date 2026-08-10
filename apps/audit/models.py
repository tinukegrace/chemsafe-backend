import uuid

from django.conf import settings
from django.db import models

from apps.inventory.models import Chemical


class AuditAction(models.TextChoices):
    CREATED = "created", "Created"
    UPDATED = "updated", "Updated"
    ARCHIVED = "archived", "Archived"
    RESTORED = "restored", "Restored"
    DELETED = "deleted", "Deleted"


class ChemicalAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # SET_NULL (not CASCADE): a "deleted" entry must survive the chemical's own
    # deletion, otherwise the audit trail for that deletion vanishes with it.
    chemical = models.ForeignKey(
        Chemical, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_log"
    )
    chemical_name = models.CharField(max_length=255)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="chemical_audit_entries"
    )
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    diff = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["chemical", "-created_at"])]

    def __str__(self):
        return f"{self.action} on {self.chemical_name} by {self.actor_id}"
