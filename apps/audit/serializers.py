from rest_framework import serializers

from .models import ChemicalAuditLog


class ChemicalAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", default="", read_only=True)
    actor_email = serializers.CharField(source="actor.email", default="", read_only=True)

    class Meta:
        model = ChemicalAuditLog
        fields = [
            "id", "chemical", "chemical_name", "actor", "actor_name", "actor_email",
            "action", "diff", "created_at",
        ]
        read_only_fields = fields
