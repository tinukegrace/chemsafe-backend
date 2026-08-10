from django.urls import path

from .views import ReportView

urlpatterns = [
    path("reports/<str:category>/", ReportView.as_view(), name="report"),
]
