from core.models.base import PublicIDModel
from django.db import models
from sites.models.sites import Department, Location, Room
from django.apps import apps
from django.core.validators import MinValueValidator, RegexValidator
from django.db.models import Sum, F
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

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"
        PENDING = "pending", "Pending"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=150)

    agreement_type = models.CharField( max_length=20, choices=AgreementType.choices, db_index=True )

    status = models.CharField( max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True )

    vendor = models.CharField( max_length=150, blank=True, db_index=True )
    reference_number = models.CharField( max_length=150, blank=True, db_index=True, help_text="Contract number, license key, etc." )

    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField( null=True, blank=True, db_index=True )

    renewal_date = models.DateField( null=True, blank=True )
    cost = models.DecimalField( max_digits=12, decimal_places=2, null=True, blank=True )

    currency = models.CharField( max_length=3, default="USD" )
    auto_renew = models.BooleanField(default=False)

    expiry_notice_days = models.PositiveIntegerField(default=30)

    notes = models.TextField(blank=True)

    # Scope
    department = models.ForeignKey( Department, on_delete=models.CASCADE, null=True, blank=True, related_name="agreements" )

    location = models.ForeignKey( Location, on_delete=models.CASCADE, null=True, blank=True, related_name="agreements" )

    room = models.ForeignKey( Room, on_delete=models.CASCADE, null=True, blank=True, related_name="agreements" )
    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["agreement_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vendor"]),
            models.Index(fields=["expiry_date"]),
        ]

        constraints = [

            # Only one scope allowed
            models.CheckConstraint(
                check=(
                    Q(department__isnull=False, location__isnull=True, room__isnull=True)
                    |
                    Q(department__isnull=True, location__isnull=False, room__isnull=True)
                    |
                    Q(department__isnull=True, location__isnull=True, room__isnull=False)
                ),
                name="agreement_single_scope"
            ),

            # Valid date range
            models.CheckConstraint(
                check=(
                    Q(start_date__isnull=True)
                    |
                    Q(expiry_date__isnull=True)
                    |
                    Q(expiry_date__gte=F("start_date"))
                ),
                name="agreement_valid_dates"
            ),

            # Renewal date should not exceed expiry
            models.CheckConstraint(
                check=(
                    Q(renewal_date__isnull=True)
                    |
                    Q(expiry_date__isnull=True)
                    |
                    Q(renewal_date__lte=F("expiry_date"))
                ),
                name="agreement_valid_renewal_date"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_agreement_type_display()})"

    @property
    def scope(self):
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
        return (
            self.expiry_date
            and self.expiry_date < timezone.now().date()
        )

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None

        return (
            self.expiry_date - timezone.now().date()
        ).days

class AssetAgreementItem(models.Model):

    agreement = models.ForeignKey( "AssetAgreement", on_delete=models.CASCADE, related_name="items", db_index=True )

    equipment = models.ForeignKey( "Equipment", on_delete=models.CASCADE, null=True, blank=True, related_name="agreement_items" )
    consumable = models.ForeignKey( "Consumable", on_delete=models.CASCADE, null=True, blank=True, related_name="agreement_items" )
    accessory = models.ForeignKey( "Accessory", on_delete=models.CASCADE, null=True, blank=True, related_name="agreement_items" )

    quantity = models.PositiveIntegerField( default=1, validators=[MinValueValidator(1)] )

    coverage_start = models.DateField( null=True, blank=True )
    coverage_end = models.DateField( null=True, blank=True )

    notes = models.TextField(blank=True)

    # Historical snapshot fields
    asset_name_snapshot = models.CharField( max_length=150, editable=False )
    asset_serial_snapshot = models.CharField( max_length=150, blank=True, editable=False )
    asset_public_id_snapshot = models.CharField( max_length=50, editable=False )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        indexes = [
            models.Index(fields=["agreement"]),
            models.Index(fields=["coverage_end"]),
        ]

        constraints = [

            # Exactly ONE asset reference
            models.CheckConstraint(
                check=(
                    Q(
                        equipment__isnull=False,
                        consumable__isnull=True,
                        accessory__isnull=True
                    )
                    |
                    Q(
                        equipment__isnull=True,
                        consumable__isnull=False,
                        accessory__isnull=True
                    )
                    |
                    Q(
                        equipment__isnull=True,
                        consumable__isnull=True,
                        accessory__isnull=False
                    )
                ),
                name="agreement_item_single_asset"
            ),

            # Valid coverage dates
            models.CheckConstraint(
                check=(
                    Q(coverage_start__isnull=True)
                    |
                    Q(coverage_end__isnull=True)
                    |
                    Q(coverage_end__gte=F("coverage_start"))
                ),
                name="agreement_item_valid_coverage_dates"
            ),

            # Unique equipment per agreement
            models.UniqueConstraint(
                fields=["agreement", "equipment"],
                condition=Q(equipment__isnull=False),
                name="unique_equipment_per_agreement"
            ),

            # Unique consumable per agreement
            models.UniqueConstraint(
                fields=["agreement", "consumable"],
                condition=Q(consumable__isnull=False),
                name="unique_consumable_per_agreement"
            ),

            # Unique accessory per agreement
            models.UniqueConstraint(
                fields=["agreement", "accessory"],
                condition=Q(accessory__isnull=False),
                name="unique_accessory_per_agreement"
            ),
        ]

    def __str__(self):
        return f"{self.agreement} → {self.asset}"

    # --------------------------------
    # Asset Resolution
    # --------------------------------

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
        return getattr(asset, "public_id", None)

    # --------------------------------
    # Location Helpers
    # --------------------------------

    @property
    def room(self):
        asset = self.asset
        return getattr(asset, "room", None)

    # --------------------------------
    # Coverage Helpers
    # --------------------------------

    @property
    def is_active(self):
        today = timezone.now().date()

        if self.coverage_start and self.coverage_start > today:
            return False

        if self.coverage_end and self.coverage_end < today:
            return False

        return True

    # --------------------------------
    # Validation
    # --------------------------------

    def clean(self):
        super().clean()

        asset = self.asset
        agreement = self.agreement

        if not asset:
            raise ValidationError(
                "Agreement item must reference an asset."
            )

        if not agreement:
            raise ValidationError(
                "Agreement is required."
            )

        asset_room = getattr(asset, "room", None)

        if not asset_room:
            raise ValidationError(
                "Asset must belong to a room."
            )

        # --------------------------------
        # Scope Validation
        # --------------------------------

        # Room scope
        if agreement.room:
            if asset_room_id := asset_room.id != agreement.room_id:
                raise ValidationError(
                    "Asset is outside the agreement room scope."
                )

        # Location scope
        elif agreement.location:
            if asset_room.location_id != agreement.location_id:
                raise ValidationError(
                    "Asset is outside the agreement location scope."
                )

        # Department scope
        elif agreement.department:
            if (
                asset_room.location.department_id
                != agreement.department_id
            ):
                raise ValidationError(
                    "Asset is outside the agreement department scope."
                )

        # --------------------------------
        # Quantity Rules
        # --------------------------------

        # Equipment is serialized
        if self.equipment and self.quantity != 1:
            raise ValidationError(
                "Equipment agreement items must have quantity of 1."
            )

        # --------------------------------
        # Coverage Validation
        # --------------------------------

        if (
            self.coverage_start
            and self.coverage_end
            and self.coverage_end < self.coverage_start
        ):
            raise ValidationError(
                "Coverage end date cannot be before coverage start date."
            )

    # --------------------------------
    # Persistence
    # --------------------------------

    def save(self, *args, **kwargs):

        asset = self.asset

        if asset:

            self.asset_name_snapshot = getattr(
                asset,
                "name",
                ""
            )

            self.asset_serial_snapshot = getattr(
                asset,
                "serial_number",
                ""
            ) or ""

            self.asset_public_id_snapshot = getattr(
                asset,
                "public_id",
                ""
            )

        self.full_clean()

        super().save(*args, **kwargs)