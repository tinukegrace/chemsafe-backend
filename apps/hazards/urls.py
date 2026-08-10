from rest_framework.routers import DefaultRouter

from .views import IncompatibilityAlertViewSet, IncompatibilityRuleViewSet

router = DefaultRouter()
router.register("hazard-rules", IncompatibilityRuleViewSet, basename="hazard-rule")
router.register("incompatibility-alerts", IncompatibilityAlertViewSet, basename="incompatibility-alert")

urlpatterns = router.urls
