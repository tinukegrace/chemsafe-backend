"""Turns a newly-created Alert or IncompatibilityAlert into per-user
Notification rows (and, if opted in, an email). Called exclusively from
apps.alerts.management.commands.refresh_alerts, and only for alerts that
were genuinely just created — never for alerts that already existed and are
simply still active. That's what guarantees "no duplicate notifications"
without any separate dedup bookkeeping: get_or_create both here and in
refresh_alerts already only ever create a row once.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification, NotificationKind, NotificationPreference

logger = logging.getLogger(__name__)


def _eligible_recipients(kind: str):
    """Active users who want in-app notifications for this alert kind.
    Auto-creates a default preference row (everything on, email off) for
    anyone who hasn't visited Settings yet, so notifications work out of
    the box rather than silently going nowhere."""
    from apps.accounts.models import User

    pairs = []
    for user in User.objects.filter(is_active=True):
        pref, _ = NotificationPreference.objects.get_or_create(user=user)
        if pref.allows(kind):
            pairs.append((user, pref))
    return pairs


def _create_and_maybe_email(user, pref, kind, title, message, *, alert=None, incompatibility_alert=None):
    notification, created = Notification.objects.get_or_create(
        recipient=user, kind=kind, alert=alert, incompatibility_alert=incompatibility_alert,
        defaults={"title": title, "message": message},
    )
    if not created:
        return notification  # already notified this user about this exact alert

    if pref.email_enabled and user.email:
        try:
            send_mail(
                subject=f"ChemSafe alert: {title}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:  # noqa: BLE001 - one bad send must not break the whole refresh run
            logger.exception("Failed to send notification email to %s", user.email)

    return notification


def notify_new_alert(alert) -> int:
    """alert: an apps.alerts.models.Alert instance that was just created.
    Returns how many recipients were notified."""
    title = f"{alert.get_alert_type_display()}: {alert.chemical.name}"
    count = 0
    for user, pref in _eligible_recipients(alert.alert_type):
        _create_and_maybe_email(user, pref, alert.alert_type, title, alert.message, alert=alert)
        count += 1
    return count


def notify_new_incompatibility(incompatibility_alert) -> int:
    """incompatibility_alert: an apps.hazards.models.IncompatibilityAlert
    instance that was just created. Returns how many recipients were
    notified."""
    title = (
        f"Incompatible storage: {incompatibility_alert.chemical_a_name} "
        f"+ {incompatibility_alert.chemical_b_name}"
    )
    message = (
        f"{incompatibility_alert.chemical_a_name} and {incompatibility_alert.chemical_b_name} "
        f"are both stored at {incompatibility_alert.location}. {incompatibility_alert.reason}"
    )
    count = 0
    for user, pref in _eligible_recipients(NotificationKind.INCOMPATIBILITY):
        _create_and_maybe_email(
            user, pref, NotificationKind.INCOMPATIBILITY, title, message,
            incompatibility_alert=incompatibility_alert,
        )
        count += 1
    return count
