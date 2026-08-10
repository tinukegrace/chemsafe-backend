from django.contrib import admin

from .models import Chemical


@admin.register(Chemical)
class ChemicalAdmin(admin.ModelAdmin):
    list_display = ("name", "cas_number", "quantity", "unit", "hazard_class", "status", "expiry_date")
    list_filter = ("hazard_class", "status")
    search_fields = ("name", "cas_number", "location")
