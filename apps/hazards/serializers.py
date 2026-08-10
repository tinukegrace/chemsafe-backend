from rest_framework import serializers

from .models import IncompatibilityAlert, IncompatibilityRule


class IncompatibilityRuleSerializer(serializers.ModelSerializer):
    """Read-only — the rule set is curated data (see RULE_SET.md / the seed
    command), not something clients author through the API."""

    class Meta:
        model = IncompatibilityRule
        fields = [
            "id", "hazard_class_a", "hazard_class_b", "principle", "description",
            "reason", "recommended_action", "reference_source", "severity", "severity_level",
        ]
        read_only_fields = fields


class IncompatibilityAlertSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = IncompatibilityAlert
        fields = [
            "id", "rule",
            "chemical_a", "chemical_a_name", "chemical_a_hazard_class",
            "chemical_b", "chemical_b_name", "chemical_b_hazard_class",
            "location", "principle", "reason", "severity", "severity_level", "recommended_action",
            "resolved", "resolved_at", "resolved_by", "archived", "status", "detected_at",
        ]
        read_only_fields = fields
