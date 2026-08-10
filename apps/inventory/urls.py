from rest_framework.routers import DefaultRouter

from .views import ChemicalViewSet

router = DefaultRouter()
router.register("chemicals", ChemicalViewSet, basename="chemical")

urlpatterns = router.urls
