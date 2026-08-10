from django.urls import path

from .views import LabelScanLinkView, OcrScanView

urlpatterns = [
    path("ocr-scan/", OcrScanView.as_view(), name="ocr-scan"),
    path("scans/<uuid:pk>/link/", LabelScanLinkView.as_view(), name="label-scan-link"),
]
