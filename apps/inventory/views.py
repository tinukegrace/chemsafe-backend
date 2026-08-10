import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import AuditAction, ChemicalAuditLog

from .models import Chemical
from .permissions import ChemicalPermission
from .serializers import ChemicalSerializer


def _json_safe(data: dict) -> dict:
    """Round-trip through Django's encoder so UUID/Decimal/date values (which
    DRF's .data can still contain, e.g. via PrimaryKeyRelatedField) become
    plain JSON-serializable types before hitting the diff JSONField."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


class ChemicalViewSet(viewsets.ModelViewSet):
    queryset = Chemical.objects.all()
    serializer_class = ChemicalSerializer
    permission_classes = [ChemicalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["hazard_class", "status"]
    search_fields = ["name", "cas_number", "location"]
    ordering_fields = ["name", "expiry_date", "quantity", "updated_at"]
    ordering = ["name"]
    # The dashboard/inventory/hazards/reports pages all load the complete
    # chemical list client-side to compute stats, charts and local filters —
    # not paginated tables. Overriding the project-wide 25/page default here
    # avoids silently truncating those views. Revisit if inventory size grows
    # large enough to need server-side pagination + a dedicated stats endpoint.
    pagination_class = None

    @action(detail=False, methods=["get"], url_path="lookup-barcode")
    def lookup_barcode(self, request):
        """Barcode-assisted inventory identification (Phase 5).

        Looks up a client-decoded barcode value against this system's own
        registered chemicals only — deliberately no external product/CAS
        lookup service, since a manufacturer barcode does not reliably
        encode chemical identity on its own.
        """
        code = (request.query_params.get("code") or "").strip()
        if not code:
            return Response({"detail": "A 'code' query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        chemical = Chemical.objects.filter(barcode=code).order_by("-updated_at").first()
        if not chemical:
            return Response(
                {"detail": "No chemical is registered with this barcode.", "code": code},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ChemicalSerializer(chemical).data)

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        ChemicalAuditLog.objects.create(
            chemical=instance,
            chemical_name=instance.name,
            actor=self.request.user,
            action=AuditAction.CREATED,
            diff=_json_safe({"created": ChemicalSerializer(instance).data}),
        )

    @transaction.atomic
    def perform_update(self, serializer):
        before = _json_safe(ChemicalSerializer(serializer.instance).data)
        instance = serializer.save()
        after = _json_safe(ChemicalSerializer(instance).data)
        changed = {
            field: {"before": before.get(field), "after": after.get(field)}
            for field in after
            if before.get(field) != after.get(field)
        }
        ChemicalAuditLog.objects.create(
            chemical=instance,
            chemical_name=instance.name,
            actor=self.request.user,
            action=AuditAction.UPDATED,
            diff=changed,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        ChemicalAuditLog.objects.create(
            chemical=None,
            chemical_name=instance.name,
            actor=self.request.user,
            action=AuditAction.DELETED,
            diff=_json_safe({"deleted": ChemicalSerializer(instance).data}),
        )
        instance.delete()
