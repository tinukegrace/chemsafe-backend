from django.contrib import admin

from .models import ChemicalAuditLog


@admin.register(ChemicalAuditLog)
class ChemicalAuditLogAdmin(admin.ModelAdmin):
    list_display = ("chemical_name", "actor", "action", "created_at")
    list_filter = ("action",)
    readonly_fields = ("id", "chemical", "chemical_name", "actor", "action", "diff", "created_at")
