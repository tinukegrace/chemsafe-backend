from django.contrib import admin

from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "kind", "read", "created_at")
    list_filter = ("kind", "read")
    search_fields = ("title", "message", "recipient__email")
    readonly_fields = ("id", "created_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "notify_expiry", "notify_low_stock", "notify_hazard", "email_enabled")
    search_fields = ("user__email",)
