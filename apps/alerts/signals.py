from django.core.management import call_command
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.inventory.models import Chemical


@receiver(post_save, sender=Chemical)
@receiver(post_delete, sender=Chemical)
def recompute_alerts_on_chemical_change(sender, **kwargs):
    """Keeps alerts/incompatibility findings immediately consistent with the
    inventory — a chemical being created, edited, moved, or deleted always
    triggers a full recompute rather than waiting for the next scheduled
    `refresh_alerts` run. Cheap at this project's scale (a full scan of the
    chemical table); a production system handling thousands of chemicals
    would instead debounce/queue this, e.g. via Celery."""
    call_command("refresh_alerts", verbosity=0)
