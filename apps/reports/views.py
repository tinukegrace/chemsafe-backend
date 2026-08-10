from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import Chemical

from .generators import REPORT_META, build_csv, build_pdf, build_xlsx

# Matches the 90-day window the frontend's expiry report used before this
# endpoint existed — keeping the same figure so the report's meaning doesn't
# silently change out from under anyone used to it.
EXPIRY_WINDOW_DAYS = 90

CONTENT_TYPES = {
    "csv": "text/csv",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
BUILDERS = {"csv": build_csv, "pdf": build_pdf, "xlsx": build_xlsx}


class ReportView(APIView):
    """GET /api/reports/<category>/?format=csv|pdf|xlsx

    Any authenticated user may generate a report — this deliberately matches
    the permission level of the underlying chemical data itself (viewable by
    any signed-in role via ChemicalPermission), rather than inventing a
    stricter tier the rest of the app doesn't otherwise have. Unauthenticated
    requests are rejected outright by IsAuthenticated.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, category: str):
        if category not in REPORT_META:
            return Response(
                {"detail": f"Unknown report category '{category}'. Expected one of: {', '.join(REPORT_META)}."},
                status=400,
            )

        fmt = (request.query_params.get("type") or "csv").lower()
        if fmt not in BUILDERS:
            return Response({"detail": "type must be one of: csv, pdf, xlsx."}, status=400)

        chemicals = self._queryset(category)
        generated_by = request.user.full_name or request.user.email

        content = BUILDERS[fmt](chemicals, category, generated_by)
        filename = f"chemsafe-{category}-{timezone.now():%Y%m%d}.{fmt}"

        response = HttpResponse(content, content_type=CONTENT_TYPES[fmt])
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def _queryset(category: str) -> list[Chemical]:
        qs = Chemical.objects.all()
        if category == "hazard":
            return list(qs.order_by("hazard_class", "name"))
        if category == "expiry":
            cutoff = timezone.localdate() + timedelta(days=EXPIRY_WINDOW_DAYS)
            return list(qs.exclude(expiry_date__isnull=True).filter(expiry_date__lte=cutoff).order_by("expiry_date"))
        if category == "low_stock":
            return [c for c in qs if c.min_stock and c.min_stock > 0 and c.quantity <= c.min_stock]
        return list(qs.order_by("name"))
