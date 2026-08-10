from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer

# A notification bell shows the recent stream, not a paginated archive —
# capped rather than paginated, matching how ChemicalViewSet/AlertViewSet
# disable pagination for their own "load it all, render client-side" pages.
RECENT_LIMIT = 100


class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/ — the current user's own notifications only."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("alert", "incompatibility_alert")
            .order_by("-created_at")[:RECENT_LIMIT]
        )


class NotificationUnreadCountView(APIView):
    """GET /api/notifications/unread-count/ — for the bell badge."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, read=False).count()
        return Response({"count": count})


class NotificationMarkReadView(APIView):
    """POST /api/notifications/<id>/read/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if notification is None:
            return Response({"detail": "Not found."}, status=404)
        if not notification.read:
            notification.read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["read", "read_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """POST /api/notifications/mark-all-read/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        updated = Notification.objects.filter(recipient=request.user, read=False).update(read=True, read_at=now)
        return Response({"updated": updated})


class NotificationPreferenceView(APIView):
    """GET/PATCH /api/notifications/preferences/ — auto-creates a default
    row (everything on, email off) on first access."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(pref).data)

    def patch(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
