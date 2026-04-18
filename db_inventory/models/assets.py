from db_inventory.models.base import PublicIDModel
from django.db import models
from sites.models.sites import Department, Location, Room
from django.apps import apps
from django.core.validators import MinValueValidator, RegexValidator
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError

serial_validator = RegexValidator(
    regex=r"^[A-Z0-9\-]+$",
    message="Serial number may contain only letters, numbers, and dashes."
)

class EquipmentStatus(models.TextChoices):
    OK = "ok", "OK"
    DAMAGED = "damaged", "Damaged"
    UNDER_REPAIR = "under_repair", "Under repair"
    LOST = "lost", "Lost"
    RETIRED = "retired", "Retired"
    CONDEMNED = "condemned", "Condemned"


class Equipment(PublicIDModel):
    PUBLIC_ID_PREFIX = "EQ"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=50, unique=True, blank=True, null=True,  validators=[serial_validator])
    status = models.CharField(max_length=20,choices=EquipmentStatus.choices,default=EquipmentStatus.OK,db_index=True, null=True)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="equipment")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["serial_number"]),
        ]
 
    @property
    def is_assigned(self) -> bool:
        EquipmentAssignment = apps.get_model(
            "assignments", "EquipmentAssignment"
        )
        try:
            return self.active_assignment.returned_at is None
        except EquipmentAssignment.DoesNotExist:
            return False
    
    @property
    def current_holder(self):
        assignment = getattr(self, "active_assignment", None)
        if assignment and assignment.returned_at is None:
            return assignment.user
        return None
        
    def audit_label(self) -> str:
        parts = [self.name]

        if self.brand:
            parts.append(self.brand)
        if self.model:
            parts.append(self.model)
        if self.serial_number:
            parts.append(f"(S/N: {self.serial_number})")
        return " ".join(parts)

    def __str__(self):
        return f"{self.name} - {self.public_id}"

class Component(PublicIDModel):
    PUBLIC_ID_PREFIX = "COM"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=50, unique=True, blank=True, null=True, validators=[serial_validator])
    quantity = models.PositiveIntegerField(default=0)
    equipment = models.ForeignKey(Equipment,on_delete=models.SET_NULL,null=True,blank=True,related_name="components")

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["serial_number"]),
        ]

        models.CheckConstraint(
        condition=models.Q(quantity__gte=0),
        name="quantity_non_negative"
        )
            

    def __str__(self):
        if self.equipment:
            return f"{self.name} @ {self.equipment.name}"
        return self.name
    
    def audit_label(self) -> str:
        parts = [self.name]
        if self.brand:
            parts.append(self.brand)
        if self.model:
            parts.append(self.model)
        if self.serial_number:
            parts.append(f"(S/N: {self.serial_number})")
        if self.equipment:
            parts.append(f"[Attached to: {self.equipment.name}]")
        return " ".join(parts)

class Consumable(PublicIDModel):
    PUBLIC_ID_PREFIX = "CON"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, max_length=255)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField( default=0, help_text="Alert when available quantity is at or below this value" )
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="consumables")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name
    
    @property
    def is_low_stock(self) -> bool:
        return (self.low_stock_threshold > 0 and self.quantity <= self.low_stock_threshold)
    
    def audit_label(self) -> str:
        return self.name

class Accessory(PublicIDModel):
    PUBLIC_ID_PREFIX = "AC"

    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="accessories")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    @property
    def assigned_quantity(self) -> int:
        return (
            self.assignments
            .filter(returned_at__isnull=True)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.assigned_quantity

    def __str__(self):
        return self.name

    def audit_label(self) -> str:
        if self.serial_number:
            return f"{self.name} (S/N: {self.serial_number})"
        return self.name


class AssetAgreement(PublicIDModel):
    PUBLIC_ID_PREFIX = "AGR"

    class AgreementType(models.TextChoices):
        WARRANTY = "warranty", "Warranty"
        LICENSE = "license", "License"
        SUBSCRIPTION = "subscription", "Subscription"
        SUPPORT = "support", "Support"
        CONTRACT = "contract", "Contract"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150)

    agreement_type = models.CharField(
        max_length=20,
        choices=AgreementType.choices,
        db_index=True
    )

    vendor = models.CharField(max_length=150, blank=True)

    reference_number = models.CharField(
        max_length=150,
        blank=True,
        help_text="Contract number, license key, etc."
    )

    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    expiry_notice_days = models.PositiveIntegerField(default=30)
    auto_renew = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    # Agreement Scope (exactly ONE must be set)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreements"
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreements"
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreements"
    )

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["agreement_type"]),
            models.Index(fields=["expiry_date"]),
        ]

        constraints = [
            models.CheckConstraint(
                check=(
                    Q(department__isnull=False, location__isnull=True, room__isnull=True) |
                    Q(department__isnull=True, location__isnull=False, room__isnull=True) |
                    Q(department__isnull=True, location__isnull=True, room__isnull=False)
                ),
                name="agreement_single_scope"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_agreement_type_display()})"

    @property
    def scope(self):
        """
        Returns the scope object (department/location/room)
        """
        return self.room or self.location or self.department

    @property
    def scope_type(self):
        if self.room:
            return "room"
        if self.location:
            return "location"
        if self.department:
            return "department"
        return None

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

class AssetAgreementItem(models.Model):

    agreement = models.ForeignKey(
        "AssetAgreement",
        on_delete=models.CASCADE,
        related_name="items"
    )

    equipment = models.ForeignKey(
        "Equipment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_items"
    )

    consumable = models.ForeignKey(
        "Consumable",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_items"
    )

    accessory = models.ForeignKey(
        "Accessory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_items"
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=["agreement"]),
        ]

        constraints = [

            # Ensure only ONE asset field is set
            models.CheckConstraint(
                check=(
                    Q(equipment__isnull=False, consumable__isnull=True, accessory__isnull=True) |
                    Q(equipment__isnull=True, consumable__isnull=False, accessory__isnull=True) |
                    Q(equipment__isnull=True, consumable__isnull=True, accessory__isnull=False)
                ),
                name="agreement_item_single_asset"
            ),

            # Prevent duplicate equipment per agreement
            models.UniqueConstraint(
                fields=["agreement", "equipment"],
                condition=Q(equipment__isnull=False),
                name="unique_equipment_per_agreement"
            ),

            # Prevent duplicate consumable per agreement
            models.UniqueConstraint(
                fields=["agreement", "consumable"],
                condition=Q(consumable__isnull=False),
                name="unique_consumable_per_agreement"
            ),

            # Prevent duplicate accessory per agreement
            models.UniqueConstraint(
                fields=["agreement", "accessory"],
                condition=Q(accessory__isnull=False),
                name="unique_accessory_per_agreement"
            ),
        ]

    def __str__(self):
        return f"{self.agreement} → {self.asset}"

    # -----------------------------
    # Asset Resolver
    # -----------------------------

    @property
    def asset(self):
        return (
            self.equipment
            or self.consumable
            or self.accessory
        )

    @property
    def asset_type(self):
        if self.equipment:
            return "equipment"
        if self.consumable:
            return "consumable"
        if self.accessory:
            return "accessory"
        return None

    @property
    def asset_public_id(self):
        asset = self.asset
        return getattr(asset, "public_id", None) if asset else None

    # -----------------------------
    # Location Helpers
    # -----------------------------

    @property
    def room(self):
        asset = self.asset
        return asset.room if asset else None

    # -----------------------------
    # Validation
    # -----------------------------

    def clean(self):
        super().clean()

        asset = self.asset
        agreement = self.agreement

        if not asset:
            raise ValidationError("Agreement item must reference an asset.")

        asset_room = asset.room
        if not asset_room:
            raise ValidationError("Asset must belong to a room.")

        # Room scoped agreement
        if agreement.room and asset_room != agreement.room:
            raise ValidationError(
                "Asset is outside the agreement room scope."
            )

        # Location scoped agreement
        if agreement.location and asset_room.location != agreement.location:
            raise ValidationError(
                "Asset is outside the agreement location scope."
            )

        # Department scoped agreement
        if (
            agreement.department
            and asset_room.location.department != agreement.department
        ):
            raise ValidationError(
                "Asset is outside the agreement department scope."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)