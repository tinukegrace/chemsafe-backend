from django.contrib import admin

from .models import IncompatibilityAlert, IncompatibilityRule


@admin.register(IncompatibilityRule)
class IncompatibilityRuleAdmin(admin.ModelAdmin):
    list_display = ("principle", "hazard_class_a", "hazard_class_b", "severity", "severity_level")
    list_filter = ("severity",)


@admin.register(IncompatibilityAlert)
class IncompatibilityAlertAdmin(admin.ModelAdmin):
    list_display = (
        "principle", "chemical_a_name", "chemical_b_name", "location",
        "severity", "resolved", "archived", "detected_at",
    )
    list_filter = ("severity", "resolved", "archived")
    readonly_fields = [f.name for f in IncompatibilityAlert._meta.fields]
