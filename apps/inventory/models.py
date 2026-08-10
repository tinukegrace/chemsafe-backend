import uuid
from datetime import date, timedelta

from django.conf import settings
from django.db import models


class HazardClass(models.TextChoices):
    NONE = "none", "None"
    FLAMMABLE = "flammable", "Flammable"
    CORROSIVE = "corrosive", "Corrosive"
    TOXIC = "toxic", "Toxic"
    OXIDIZER = "oxidizer", "Oxidizer"
    REACTIVE = "reactive", "Reactive"
    HEALTH = "health", "Health hazard"
    ENVIRONMENTAL = "environmental", "Environmental hazard"


class ChemicalStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    NEAR_EXPIRY = "near_expiry", "Near expiry"
    LOW_STOCK = "low_stock", "Low stock"
    ARCHIVED = "archived", "Archived"


class Chemical(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    cas_number = models.CharField(max_length=50, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit = models.CharField(max_length=20, default="g")
    location = models.CharField(max_length=255, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    hazard_class = models.CharField(max_length=20, choices=HazardClass.choices, default=HazardClass.NONE)
    ghs_category = models.JSONField(default=list, blank=True)
    min_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    supplier = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ChemicalStatus.choices, default=ChemicalStatus.ACTIVE)
    barcode = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_chemicals"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["hazard_class"]),
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["barcode"]),
        ]

    def __str__(self):
        return self.name

    def compute_status(self) -> str:
        """Mirrors the old Postgres `compute_chemical_status` trigger exactly."""
        today = date.today()
        if self.expiry_date and self.expiry_date < today:
            return ChemicalStatus.EXPIRED
        if self.expiry_date and self.expiry_date <= today + timedelta(days=30):
            return ChemicalStatus.NEAR_EXPIRY
        if self.min_stock and self.min_stock > 0 and self.quantity <= self.min_stock:
            return ChemicalStatus.LOW_STOCK
        return ChemicalStatus.ACTIVE

    def save(self, *args, **kwargs):
        # An explicit archive (status already set to ARCHIVED before save) is the
        # one escape hatch — everything else is always server-derived, never
        # client-settable, exactly like the old trigger.
        if self.status != ChemicalStatus.ARCHIVED:
            self.status = self.compute_status()
        super().save(*args, **kwargs)
