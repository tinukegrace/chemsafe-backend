from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    chemical_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "message", "read", "read_at", "created_at", "chemical_id"]
        read_only_fields = fields

    def get_chemical_id(self, obj):
        """Convenience for the frontend's 'View' link — resolves to whichever
        chemical the underlying alert concerns, regardless of whether this
        notification came from a single-chemical alert or an incompatibility
        pair (in which case it links to the first of the two)."""
        if obj.alert_id:
            return obj.alert.chemical_id
        if obj.incompatibility_alert_id:
            return obj.incompatibility_alert.chemical_a_id or obj.incompatibility_alert.chemical_b_id
        return None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["notify_expiry", "notify_low_stock", "notify_hazard", "email_enabled"]
