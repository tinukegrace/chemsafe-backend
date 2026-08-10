from django.core.management import call_command
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdministrator

from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only + resolve/archive actions. Rows themselves are only ever
    written by the `refresh_alerts` management command — this is a safety
    feed, not a place for clients to author arbitrary alerts."""

    queryset = Alert.objects.select_related("chemical", "resolved_by").all()
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["alert_type", "resolved", "archived"]
    pagination_class = None

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


class RefreshAlertsView(APIView):
    """Admin-triggered on-demand recompute of every alert (expiry/low-stock/
    hazard + storage incompatibility). In production this same logic runs via
    the `refresh_alerts` management command on a schedule (cron/Task
    Scheduler) — this endpoint exists for demoing/forcing a recompute without
    shell access."""

    permission_classes = [IsAdministrator]

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description="Alerts recomputed.")},
    )
    def post(self, request):
        call_command("refresh_alerts")
        return Response({"detail": "Alerts recomputed."})
