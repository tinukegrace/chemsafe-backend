from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import IncompatibilityAlert, IncompatibilityRule
from .serializers import IncompatibilityAlertSerializer, IncompatibilityRuleSerializer


class IncompatibilityRuleViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view of the documented rule set (see RULE_SET.md) — lets the
    frontend/API consumer show *why* an alert fired, not just that it did."""

    queryset = IncompatibilityRule.objects.all().order_by("-severity_level", "principle")
    serializer_class = IncompatibilityRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class IncompatibilityAlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IncompatibilityAlert.objects.select_related(
        "rule", "chemical_a", "chemical_b", "resolved_by"
    ).all()
    serializer_class = IncompatibilityAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["severity", "resolved", "archived", "location"]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save(update_fields=["resolved", "resolved_at", "resolved_by"])
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        alert = self.get_object()
        alert.archived = True
        alert.save(update_fields=["archived"])
        return Response(self.get_serializer(alert).data)
