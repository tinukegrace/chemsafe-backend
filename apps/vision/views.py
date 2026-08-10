import io

import pytesseract
from PIL import Image, UnidentifiedImageError
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LabelScan
from .ocr_pipeline import run_pipeline
from .serializers import LabelScanLinkSerializer, LabelScanUploadSerializer

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class OcrScanView(APIView):
    """POST a chemical label photo, get back extracted fields for review.

    Assistive only: nothing here writes to the chemical inventory. The
    frontend shows every field (with its confidence score) for the user to
    verify/edit, and only the subsequent POST /api/chemicals/ — a normal,
    already-audited create — actually creates or updates a record.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = LabelScanUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["image"]

        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {"detail": "Unsupported image type. Please upload a JPEG, PNG, or WEBP file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > MAX_UPLOAD_BYTES:
            return Response(
                {"detail": "Image is too large (max 8MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_bytes = upload.read()

        # Explicit verify()+reopen guards against corrupt or maliciously
        # crafted image files — verify() invalidates the file object, so a
        # second, fresh open is required to actually load pixel data.
        try:
            probe = Image.open(io.BytesIO(raw_bytes))
            probe.verify()
            pil_image = Image.open(io.BytesIO(raw_bytes))
            pil_image.load()
        except (UnidentifiedImageError, OSError):
            return Response(
                {"detail": "Could not read this file as an image. It may be corrupted or an unsupported format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = run_pipeline(pil_image)
        except pytesseract.TesseractNotFoundError:
            return Response(
                {"detail": "The OCR engine is not available on the server. Contact an administrator."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        upload.seek(0)
        scan = LabelScan.objects.create(
            image=upload,
            raw_text=result.raw_text,
            extracted_data={
                "name": result.name,
                "cas_number": result.cas_number,
                "cas_checksum_valid": result.cas_checksum_valid,
                "expiry_date": result.expiry_date,
                "manufacturer": result.manufacturer,
                "ghs_codes": result.ghs_codes,
                "hazard_keywords": result.hazard_keywords,
            },
            confidence=result.confidence,
            created_by=request.user,
        )

        return Response(
            {
                "id": str(scan.id),
                "image": request.build_absolute_uri(scan.image.url),
                "raw_text": result.raw_text,
                "name": result.name,
                "cas_number": result.cas_number,
                "cas_checksum_valid": result.cas_checksum_valid,
                "expiry_date": result.expiry_date,
                "manufacturer": result.manufacturer,
                "ghs_codes": result.ghs_codes,
                "hazard_keywords": result.hazard_keywords,
                "confidence": result.confidence,
            },
            status=status.HTTP_201_CREATED,
        )


class LabelScanLinkView(APIView):
    """Links a scan to the chemical the user actually saved, once they've
    confirmed the (possibly edited) extracted fields — closes the audit
    trail without letting the OCR step write to inventory on its own."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            scan = LabelScan.objects.get(pk=pk)
        except LabelScan.DoesNotExist:
            return Response({"detail": "Scan not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LabelScanLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan.chemical_id = serializer.validated_data["chemical_id"]
        scan.save(update_fields=["chemical"])
        return Response(status=status.HTTP_204_NO_CONTENT)
