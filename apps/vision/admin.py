from django.contrib import admin

from .models import LabelScan


@admin.register(LabelScan)
class LabelScanAdmin(admin.ModelAdmin):
    list_display = ("id", "chemical", "created_by", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("id", "image", "raw_text", "extracted_data", "confidence", "created_at")
    search_fields = ("raw_text",)
