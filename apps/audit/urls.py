from django.urls import path

from . import views

urlpatterns = [
    path("", views.ChemicalAuditLogListView.as_view(), name="audit-log-list"),
]
