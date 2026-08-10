from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    chemical_name = serializers.CharField(source="chemical.name", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "chemical", "chemical_name", "alert_type", "message",
            "resolved", "resolved_at", "resolved_by", "archived", "created_at",
        ]
        read_only_fields = fields
