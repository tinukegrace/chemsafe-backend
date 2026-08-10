from rest_framework import generics, permissions

from .models import ChemicalAuditLog
from .serializers import ChemicalAuditLogSerializer


class ChemicalAuditLogListView(generics.ListAPIView):
    """Own entries for lab_staff; every entry for administrators.

    Mirrors the RLS fix applied earlier in this project's history: actors see
    their own actions, administrators see the full trail. Supports an optional
    ?chemical=<id> filter for a single chemical's history.
    """

    serializer_class = ChemicalAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ChemicalAuditLog.objects.none()
        qs = ChemicalAuditLog.objects.select_related("actor", "chemical")
        if not self.request.user.is_administrator:
            qs = qs.filter(actor=self.request.user)
        chemical_id = self.request.query_params.get("chemical")
        if chemical_id:
            qs = qs.filter(chemical_id=chemical_id)
        return qs
