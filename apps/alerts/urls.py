from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AlertViewSet, RefreshAlertsView

router = DefaultRouter()
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    # Must precede router.urls — otherwise the router's `alerts/<pk>/` detail
    # route greedily matches "refresh" as a pk value first.
    path("alerts/refresh/", RefreshAlertsView.as_view(), name="alerts-refresh"),
] + router.urls
