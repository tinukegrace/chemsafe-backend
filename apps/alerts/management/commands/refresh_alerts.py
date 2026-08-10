from collections import defaultdict
from datetime import date, timedelta
from itertools import combinations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.alerts.models import Alert, AlertType
from apps.hazards.models import IncompatibilityAlert, IncompatibilityRule
from apps.inventory.models import Chemical, ChemicalStatus
from apps.notifications.services import notify_new_alert, notify_new_incompatibility

NEAR_EXPIRY_WINDOW_DAYS = 30
HAZARDOUS_SINGLE_CLASSES = {"toxic", "reactive"}


def _days_until(d):
    if d is None:
        return None
    return (d - date.today()).days


class Command(BaseCommand):
    help = (
        "Recomputes all live alerts: expiry/near-expiry/low-stock/hazard "
        "(single chemical, apps.alerts) and storage incompatibilities "
        "(chemical pairs sharing a location, apps.hazards). Idempotent — "
        "safe to run repeatedly (e.g. from a scheduled task)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        single_created, single_removed = self._refresh_single_chemical_alerts()
        pair_created, pair_removed = self._refresh_incompatibility_alerts()
        self.stdout.write(self.style.SUCCESS(
            f"Single-chemical alerts: +{single_created} created, -{single_removed} cleared. "
            f"Incompatibility alerts: +{pair_created} created, -{pair_removed} cleared."
        ))

    def _refresh_single_chemical_alerts(self):
        wanted = set()  # (chemical_id, alert_type)
        to_create = []

        for c in Chemical.objects.exclude(status=ChemicalStatus.ARCHIVED):
            days = _days_until(c.expiry_date)
            if days is not None and days < 0:
                wanted.add((c.id, AlertType.EXPIRED))
                to_create.append((c, AlertType.EXPIRED, f"{c.name} expired {abs(days)} day(s) ago."))
            elif days is not None and days <= NEAR_EXPIRY_WINDOW_DAYS:
                wanted.add((c.id, AlertType.NEAR_EXPIRY))
                to_create.append((c, AlertType.NEAR_EXPIRY, f"{c.name} expires in {days} day(s)."))

            if c.min_stock and c.min_stock > 0 and c.quantity <= c.min_stock:
                wanted.add((c.id, AlertType.LOW_STOCK))
                to_create.append((
                    c, AlertType.LOW_STOCK,
                    f"{c.name} low stock: {c.quantity} {c.unit} on hand, minimum {c.min_stock} {c.unit}.",
                ))

            if c.hazard_class in HAZARDOUS_SINGLE_CLASSES:
                wanted.add((c.id, AlertType.HAZARD))
                to_create.append((
                    c, AlertType.HAZARD,
                    f"{c.name} requires strict controls (hazard class: {c.get_hazard_class_display()}).",
                ))

        created = 0
        for chemical, alert_type, message in to_create:
            alert, was_created = Alert.objects.get_or_create(
                chemical=chemical, alert_type=alert_type, defaults={"message": message},
            )
            if was_created:
                created += 1
                notify_new_alert(alert)

        # Delete alerts whose triggering condition no longer holds. Only rows
        # with a live chemical are candidates — an alert whose chemical was
        # deleted is frozen history via chemical's own audit trail, not ours
        # to prune (Alert.chemical is CASCADE, so it's already gone anyway).
        removed = 0
        for alert in Alert.objects.all():
            if (alert.chemical_id, alert.alert_type) not in wanted:
                alert.delete()
                removed += 1

        return created, removed

    def _refresh_incompatibility_alerts(self):
        rules_by_pair = {}
        for rule in IncompatibilityRule.objects.all():
            rules_by_pair[frozenset((rule.hazard_class_a, rule.hazard_class_b))] = rule

        by_location = defaultdict(list)
        for c in Chemical.objects.exclude(status=ChemicalStatus.ARCHIVED).exclude(location=""):
            by_location[c.location].append(c)

        valid_keys = set()  # (chemical_a_id, chemical_b_id, rule_id)
        created = 0

        for location, chemicals in by_location.items():
            for a, b in combinations(chemicals, 2):
                pair_key = frozenset((a.hazard_class, b.hazard_class))
                rule = rules_by_pair.get(pair_key)
                if rule is None:
                    continue

                # Normalize ordering so the same real-world pair always maps
                # to one row regardless of iteration order.
                chem_a, chem_b = sorted([a, b], key=lambda c: str(c.id))
                valid_keys.add((chem_a.id, chem_b.id, rule.id))

                incompatibility_alert, was_created = IncompatibilityAlert.objects.get_or_create(
                    chemical_a=chem_a, chemical_b=chem_b, rule=rule,
                    defaults=dict(
                        chemical_a_name=chem_a.name,
                        chemical_a_hazard_class=chem_a.hazard_class,
                        chemical_b_name=chem_b.name,
                        chemical_b_hazard_class=chem_b.hazard_class,
                        location=location,
                        principle=rule.principle,
                        reason=rule.reason,
                        severity=rule.severity,
                        severity_level=rule.severity_level,
                        recommended_action=rule.recommended_action,
                    ),
                )
                if was_created:
                    created += 1
                    notify_new_incompatibility(incompatibility_alert)

        # Only prune live pairs (both chemicals still present) that no
        # longer match — rows where a chemical was deleted (SET NULL) are
        # frozen history and left untouched, same reasoning as the audit log.
        removed = 0
        live_qs = IncompatibilityAlert.objects.filter(
            chemical_a__isnull=False, chemical_b__isnull=False,
        )
        for alert in live_qs:
            if (alert.chemical_a_id, alert.chemical_b_id, alert.rule_id) not in valid_keys:
                alert.delete()
                removed += 1

        return created, removed
