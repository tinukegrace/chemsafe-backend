import uuid

from django.conf import settings
from django.db import models


class LabelScan(models.Model):
    """A single OCR scan event.

    Persisted independently of Chemical because a scan happens *before* a
    chemical record necessarily exists — the user reviews/edits the
    extracted fields first, and only then decides to save them as a new (or
    updated) chemical. `chemical` is linked retroactively at that point via
    `link_to_chemical`, closing the audit trail described in the thesis
    (extracted_data is kept as a JSON audit copy distinct from the final,
    user-confirmed values that end up on the CHEMICAL record).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chemical = models.ForeignKey(
        "inventory.Chemical", null=True, blank=True, on_delete=models.SET_NULL, related_name="label_scans"
    )
    image = models.ImageField(upload_to="label_scans/%Y/%m/")
    raw_text = models.TextField(blank=True)
    # Structured fields as extracted by the pipeline, before any user edits —
    # an audit copy, not the confirmed values (those go on Chemical itself).
    extracted_data = models.JSONField(default=dict, blank=True)
    # Per-field confidence scores in [0, 1], keyed by field name.
    confidence = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="label_scans"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Scan {self.id} ({self.created_at:%Y-%m-%d})"
