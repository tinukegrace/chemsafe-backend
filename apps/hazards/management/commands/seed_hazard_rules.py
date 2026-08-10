from django.core.management.base import BaseCommand

from apps.hazards.models import IncompatibilityRule

# This IS the rule set — kept in exact lockstep with RULE_SET.md. Do not add
# rows here without adding the corresponding row to that document, and vice
# versa; the two must always match, since RULE_SET.md is what the design
# review / defense points to as the source of truth.
RULES = [
    dict(
        hazard_class_a="flammable", hazard_class_b="oxidizer",
        principle="Oxidizer–flammable segregation",
        description="Detects co-located flammable and oxidizing chemicals.",
        reason=(
            "Oxidizers supply or generate oxygen and dramatically accelerate combustion; "
            "co-storage with flammable material is one of the most universally cited "
            "fire/explosion risks in laboratory safety guidance."
        ),
        recommended_action=(
            "Relocate one substance immediately to a dedicated, separate storage area. "
            "Oxidizers must not share a cabinet, shelf, or spill-containment tray with any "
            "flammable liquid or solid."
        ),
        reference_source=(
            "OSHA Laboratory Standard (29 CFR 1910.1450); NFPA hazardous materials storage "
            "guidance; Flinn Scientific chemical storage segregation groups"
        ),
        severity="critical",
    ),
    dict(
        hazard_class_a="oxidizer", hazard_class_b="reactive",
        principle="Oxidizer–reactive segregation",
        description="Detects co-located oxidizing and reactive (water-reactive/pyrophoric/self-reactive) chemicals.",
        reason=(
            "Reactive substances can react violently with oxidizers or have their "
            "decomposition accelerated by them, risking an uncontrolled exotherm."
        ),
        recommended_action=(
            "Isolate the reactive substance in dedicated, manufacturer-specified storage "
            "(e.g. inert atmosphere or mineral oil as directed by its SDS), physically "
            "separate from all oxidizers."
        ),
        reference_source="NOAA/CAMEO chemical compatibility chart; NFPA hazardous materials storage guidance",
        severity="critical",
    ),
    dict(
        hazard_class_a="flammable", hazard_class_b="reactive",
        principle="Flammable–reactive segregation",
        description="Detects co-located flammable and reactive chemicals.",
        reason=(
            "Reactive substances can generate heat, sparks, or spontaneous ignition, "
            "which is sufficient to ignite nearby flammable material."
        ),
        recommended_action=(
            "Store reactive materials away from all flammable liquids/solids; confirm "
            "storage conditions against the reactive substance's SDS."
        ),
        reference_source="NFPA hazardous materials storage guidance; Flinn Scientific storage segregation groups",
        severity="high",
    ),
    dict(
        hazard_class_a="corrosive", hazard_class_b="reactive",
        principle="Corrosive–reactive segregation",
        description="Detects co-located corrosive and reactive chemicals.",
        reason=(
            "Corrosives (notably aqueous acids/bases) can react violently with "
            "water-reactive or active-metal-sensitive materials — generating heat, "
            "flammable gas (e.g. hydrogen), or a violent neutralization exotherm."
        ),
        recommended_action=(
            "Store in separate secondary containment; do not combine without a "
            "documented risk assessment and appropriate engineering controls."
        ),
        reference_source="NOAA/CAMEO chemical compatibility chart",
        severity="high",
    ),
    dict(
        hazard_class_a="corrosive", hazard_class_b="oxidizer",
        principle="Corrosive–oxidizer segregation",
        description="Detects co-located corrosive and oxidizing chemicals.",
        reason=(
            "Some concentrated corrosive acids are themselves strong oxidizers or react "
            "with other oxidizers, releasing heat or toxic gas."
        ),
        recommended_action=(
            "Maintain separate acid and oxidizer storage (e.g. dedicated acid cabinet), "
            "per standard chemical storage segregation practice."
        ),
        reference_source="OSHA Laboratory Standard (29 CFR 1910.1450); NFPA hazardous materials storage guidance",
        severity="high",
    ),
    dict(
        hazard_class_a="toxic", hazard_class_b="oxidizer",
        principle="Toxic-release acceleration",
        description="Detects co-located toxic and oxidizing chemicals.",
        reason=(
            "An oxidizer reacting nearby can accelerate the release, volatilization, or "
            "violent dispersal of a toxic substance in the event of a spill or fire, "
            "compounding the incident."
        ),
        recommended_action=(
            "Store separately; ensure fume-hood ventilation is available wherever both "
            "hazard classes are handled in proximity."
        ),
        reference_source="NOAA/CAMEO chemical compatibility chart",
        severity="medium",
    ),
    dict(
        hazard_class_a="toxic", hazard_class_b="corrosive",
        principle="Compounded exposure / spill-response complexity",
        description="Detects co-located toxic and corrosive chemicals.",
        reason=(
            "Co-locating toxic and corrosive substances compounds first-aid response "
            "(simultaneous chemical burn + systemic toxic exposure) and complicates "
            "spill cleanup and PPE selection."
        ),
        recommended_action=(
            "Segregate storage; keep substance-specific spill kits and SDS co-located "
            "with each chemical, not shared."
        ),
        reference_source="OSHA Laboratory Standard (29 CFR 1910.1450)",
        severity="medium",
    ),
]


class Command(BaseCommand):
    help = "Seed the 7 documented hazard incompatibility rules (see RULE_SET.md)."

    def handle(self, *args, **options):
        created_count = 0
        for rule in RULES:
            _, created = IncompatibilityRule.objects.update_or_create(
                hazard_class_a=rule["hazard_class_a"],
                hazard_class_b=rule["hazard_class_b"],
                defaults={k: v for k, v in rule.items() if k not in ("hazard_class_a", "hazard_class_b")},
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_count} new rules ({len(RULES) - created_count} already existed / updated)."
        ))
