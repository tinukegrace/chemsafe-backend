import uuid

from django.conf import settings
from django.db import models


class NotificationKind(models.TextChoices):
    EXPIRED = "expired", "Expired"
    NEAR_EXPIRY = "near_expiry", "Near expiry"
    LOW_STOCK = "low_stock", "Low stock"
    HAZARD = "hazard", "Hazard"
    INCOMPATIBILITY = "incompatibility", "Storage incompatibility"


class NotificationPreference(models.Model):
    """Per-user opt-in/out for each alert category, plus whether email
    should be sent in addition to the in-app notification. Replaces the
    old localStorage-only toggles on the Settings page — these now persist
    on the account itself and actually govern whether a notification/email
    gets created at all (see refresh_alerts, which reads these)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference")
    notify_expiry = models.BooleanField(default=True)
    notify_low_stock = models.BooleanField(default=True)
    notify_hazard = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification preferences for {self.user_id}"

    def allows(self, kind: str) -> bool:
        if kind in (NotificationKind.EXPIRED, NotificationKind.NEAR_EXPIRY):
            return self.notify_expiry
        if kind == NotificationKind.LOW_STOCK:
            return self.notify_low_stock
        if kind in (NotificationKind.HAZARD, NotificationKind.INCOMPATIBILITY):
            return self.notify_hazard
        return True


class Notification(models.Model):
    """A single in-app notification for one user, about one newly-detected
    alert. Created exactly once per (user, alert) pair — see
    apps.alerts.management.commands.refresh_alerts, which only calls the
    creation helper here when an underlying Alert/IncompatibilityAlert row
    was itself genuinely new, not on every refresh run. That's what keeps
    this duplicate-free without any extra bookkeeping."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=NotificationKind.choices)
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=500)

    # Exactly one of these is set, depending on `kind` — see the two FKs
    # rather than a generic-relation, since there are only ever two possible
    # sources and this keeps querying/joining simple and explicit.
    alert = models.ForeignKey("alerts.Alert", null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    incompatibility_alert = models.ForeignKey(
        "hazards.IncompatibilityAlert", null=True, blank=True, on_delete=models.CASCADE, related_name="notifications"
    )

    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Belt-and-suspenders alongside the create-once-per-new-alert
            # discipline in refresh_alerts: the DB itself won't allow a
            # second notification for the same user+alert pair.
            models.UniqueConstraint(
                fields=["recipient", "alert"],
                condition=models.Q(alert__isnull=False),
                name="unique_notification_per_user_alert",
            ),
            models.UniqueConstraint(
                fields=["recipient", "incompatibility_alert"],
                condition=models.Q(incompatibility_alert__isnull=False),
                name="unique_notification_per_user_incompatibility",
            ),
        ]

    def __str__(self):
        return f"{self.kind} -> {self.recipient_id} ({'read' if self.read else 'unread'})"
