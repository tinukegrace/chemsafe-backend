from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.inventory.models import Chemical

TODAY = date.today()

# name, cas_number, quantity, unit, location, expiry_offset_days, hazard_class,
# ghs_category, min_stock, supplier, notes
SEED_DATA = [
    ("Acetone", "67-64-1", 2500, "mL", "Cabinet A-1 (Flammables)", 180, "flammable", ["H225", "H319", "H336"], 500, {"name": "Sigma-Aldrich", "contact": "orders@sial.com"}, "Common solvent; keep away from ignition sources."),
    ("Methanol", "67-56-1", 1000, "mL", "Cabinet A-1 (Flammables)", 90, "toxic", ["H225", "H301", "H311", "H331", "H370"], 250, {"name": "Fisher Scientific"}, "Highly toxic if swallowed or inhaled."),
    ("Ethanol (Absolute)", "64-17-5", 5000, "mL", "Cabinet A-1 (Flammables)", 365, "flammable", ["H225", "H319"], 1000, {"name": "VWR"}, "Denatured grade available on request."),
    ("Isopropanol", "67-63-0", 3000, "mL", "Cabinet A-1 (Flammables)", 200, "flammable", ["H225", "H319", "H336"], 500, {"name": "Sigma-Aldrich"}, ""),
    ("Sulfuric Acid 98%", "7664-93-9", 500, "mL", "Cabinet B-2 (Acids)", 400, "corrosive", ["H290", "H314"], 250, {"name": "Merck"}, "Add acid to water, never the reverse."),
    ("Hydrochloric Acid 37%", "7647-01-0", 1000, "mL", "Cabinet B-2 (Acids)", 240, "corrosive", ["H290", "H314", "H335"], 500, {"name": "Merck"}, ""),
    ("Nitric Acid 70%", "7697-37-2", 500, "mL", "Cabinet B-2 (Acids)", 180, "oxidizer", ["H272", "H290", "H314", "H331"], 250, {"name": "Fisher Scientific"}, "Strong oxidizer; store away from organics."),
    ("Sodium Hydroxide", "1310-73-2", 2000, "g", "Cabinet B-3 (Bases)", 800, "corrosive", ["H290", "H314"], 500, {"name": "Sigma-Aldrich"}, "Hygroscopic pellets."),
    ("Potassium Hydroxide", "1310-58-3", 1000, "g", "Cabinet B-3 (Bases)", 700, "corrosive", ["H290", "H302", "H314"], 250, {"name": "VWR"}, ""),
    ("Ammonium Hydroxide 28%", "1336-21-6", 500, "mL", "Cabinet B-3 (Bases)", 120, "corrosive", ["H290", "H314", "H335", "H400"], 250, {"name": "Merck"}, "Volatile; use fume hood."),
    ("Hydrogen Peroxide 30%", "7722-84-1", 1000, "mL", "Cabinet C-1 (Oxidizers)", 60, "oxidizer", ["H302", "H318", "H335"], 500, {"name": "Sigma-Aldrich"}, "Refrigerate; avoid contamination."),
    ("Potassium Permanganate", "7722-64-7", 500, "g", "Cabinet C-1 (Oxidizers)", 500, "oxidizer", ["H272", "H302", "H410"], 100, {"name": "Fisher Scientific"}, ""),
    ("Sodium Chloride", "7647-14-5", 5000, "g", "Shelf D-1", 1000, "none", [], 1000, {"name": "VWR"}, "ACS reagent grade."),
    ("Sodium Bicarbonate", "144-55-8", 3000, "g", "Shelf D-1", 900, "none", [], 500, {"name": "Sigma-Aldrich"}, ""),
    ("Glucose (D-)", "50-99-7", 2000, "g", "Shelf D-2", 400, "none", [], 500, {"name": "Sigma-Aldrich"}, ""),
    ("Ethyl Acetate", "141-78-6", 2500, "mL", "Cabinet A-1 (Flammables)", 300, "flammable", ["H225", "H319", "H336"], 500, {"name": "Fisher Scientific"}, ""),
    ("Toluene", "108-88-3", 2000, "mL", "Cabinet A-1 (Flammables)", 250, "health", ["H225", "H304", "H315", "H336", "H361d", "H373"], 500, {"name": "Sigma-Aldrich"}, "Reproductive toxicity — see SDS."),
    ("Dichloromethane", "75-09-2", 1000, "mL", "Cabinet E-1 (Halogenated)", 150, "health", ["H315", "H319", "H335", "H336", "H351", "H373"], 250, {"name": "Merck"}, "Suspected carcinogen."),
    ("Chloroform", "67-66-3", 500, "mL", "Cabinet E-1 (Halogenated)", 120, "toxic", ["H302", "H315", "H319", "H331", "H336", "H351", "H361d", "H372"], 250, {"name": "Sigma-Aldrich"}, "Store in dark; forms phosgene."),
    ("Diethyl Ether", "60-29-7", 500, "mL", "Cabinet A-1 (Flammables)", 45, "flammable", ["H224", "H302", "H336"], 250, {"name": "Fisher Scientific"}, "Peroxide former; check before distillation."),
    ("n-Hexane", "110-54-3", 1000, "mL", "Cabinet A-1 (Flammables)", 200, "health", ["H225", "H304", "H315", "H336", "H361f", "H373", "H411"], 500, {"name": "VWR"}, ""),
    ("Formaldehyde 37%", "50-00-0", 500, "mL", "Cabinet F-1 (Carcinogens)", 90, "toxic", ["H301", "H311", "H314", "H317", "H331", "H350", "H370"], 250, {"name": "Sigma-Aldrich"}, "Known carcinogen; strict controls."),
    ("Phenol", "108-95-2", 250, "g", "Cabinet F-1 (Carcinogens)", 300, "toxic", ["H301", "H311", "H314", "H331", "H341", "H373"], 100, {"name": "Merck"}, ""),
    ("Silver Nitrate", "7761-88-8", 100, "g", "Safe G-1 (Precious)", 700, "oxidizer", ["H272", "H290", "H314", "H410"], 25, {"name": "Sigma-Aldrich"}, "Store in amber bottle."),
    ("Copper(II) Sulfate", "7758-98-7", 500, "g", "Shelf D-3", 500, "environmental", ["H302", "H315", "H319", "H410"], 100, {"name": "VWR"}, ""),
    ("Iron(III) Chloride", "7705-08-0", 500, "g", "Shelf D-3", 400, "corrosive", ["H290", "H302", "H315", "H318"], 100, {"name": "Fisher Scientific"}, ""),
    ("Ammonium Persulfate", "7727-54-0", 500, "g", "Cabinet C-1 (Oxidizers)", 15, "oxidizer", ["H272", "H302", "H315", "H317", "H319", "H334", "H335"], 250, {"name": "Sigma-Aldrich"}, "NEAR EXPIRY — reorder."),
    ("Sodium Azide", "26628-22-8", 25, "g", "Safe G-2 (Highly toxic)", 200, "toxic", ["H300", "H310", "H373", "H400", "H410"], 10, {"name": "Sigma-Aldrich"}, "DO NOT flush — forms explosive azides with metals."),
    ("Acetonitrile (HPLC)", "75-05-8", 4000, "mL", "Cabinet A-1 (Flammables)", -5, "flammable", ["H225", "H302", "H312", "H319", "H332"], 1000, {"name": "Fisher Scientific"}, "EXPIRED — dispose according to SOP."),
    ("Sodium Sulfate (Anhydrous)", "7757-82-6", 2000, "g", "Shelf D-2", 900, "none", [], 500, {"name": "VWR"}, "Drying agent."),
    ("Magnesium Sulfate (Anhydrous)", "7487-88-9", 1000, "g", "Shelf D-2", 900, "none", [], 250, {"name": "Sigma-Aldrich"}, "Drying agent."),
    ("Tetrahydrofuran (THF)", "109-99-9", 20, "mL", "Cabinet A-1 (Flammables)", 180, "flammable", ["H225", "H302", "H319", "H335", "H351"], 250, {"name": "Sigma-Aldrich"}, "LOW STOCK — reorder."),
]


class Command(BaseCommand):
    help = "Seed the database with representative lab chemicals for local development/demo."

    def handle(self, *args, **options):
        created_count = 0
        for name, cas, qty, unit, location, offset, hazard, ghs, min_stock, supplier, notes in SEED_DATA:
            _, created = Chemical.objects.get_or_create(
                name=name,
                cas_number=cas,
                defaults={
                    "quantity": qty,
                    "unit": unit,
                    "location": location,
                    "expiry_date": TODAY + timedelta(days=offset),
                    "hazard_class": hazard,
                    "ghs_category": ghs,
                    "min_stock": min_stock,
                    "supplier": supplier,
                    "notes": notes,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_count} new chemicals ({len(SEED_DATA) - created_count} already existed)."
        ))
