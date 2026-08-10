import json

from rest_framework import serializers

from .models import Chemical


class ChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemical
        fields = [
            "id", "name", "cas_number", "quantity", "unit", "location", "expiry_date",
            "hazard_class", "ghs_category", "min_stock", "supplier", "notes", "status",
            "barcode", "created_by", "created_at", "updated_at",
        ]
        # status is always server-computed (see Chemical.save); created_by is set
        # from the authenticated user in the view, never trusted from the client.
        read_only_fields = ["id", "status", "created_by", "created_at", "updated_at"]

    def validate_barcode(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            return value
        qs = self.Meta.model.objects.filter(barcode=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Another chemical is already registered with this barcode.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Defensive normalization: with Django 5.2 + psycopg3, JSONField can in
        # some driver/version combinations return the raw un-decoded JSON text
        # for a jsonb column instead of an already-parsed list/dict. Guarantee
        # the wire contract (ghs_category is always an array, supplier always
        # an object) regardless of what the driver handed back.
        data["ghs_category"] = self._as_list(data.get("ghs_category"))
        data["supplier"] = self._as_dict(data.get("supplier"))
        return data

    @staticmethod
    def _as_list(value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    @staticmethod
    def _as_dict(value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return {}
