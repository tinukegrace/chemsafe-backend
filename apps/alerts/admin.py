from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("chemical", "alert_type", "resolved", "archived", "created_at")
    list_filter = ("alert_type", "resolved", "archived")
    readonly_fields = [f.name for f in Alert._meta.fields]
