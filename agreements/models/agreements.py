from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.conf import settings
from core.models import PublicIDModel
from sites.models.sites import Department, Location, Room



class AgreementType(models.TextChoices):
    LICENSE = "LICENSE", "License"
    WARRANTY = "WARRANTY", "Warranty"
    SERVICE = "SERVICE", "Service"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    SUPPORT = "SUPPORT", "Support"
    OTHER = "OTHER", "Other"


class AgreementStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    PENDING = "PENDING", "Pending"
    TERMINATED = "TERMINATED", "Terminated"


class CoverageScopeType(models.TextChoices):
    GLOBAL = "GLOBAL", "Global"
    DEPARTMENT = "DEPARTMENT", "Department"
    LOCATION = "LOCATION", "Location"
    ROOM = "ROOM", "Room"


class AssetAgreement(PublicIDModel):
    """
    Represents the actual legal/business agreement.

    Examples:
    - Microsoft Enterprise License
    - Dell Warranty
    - ISP Service Contract
    - HVAC Maintenance Agreement
    """

    PUBLIC_ID_PREFIX = "AGR"

    name = models.CharField(max_length=255)

    agreement_type = models.CharField( max_length=30, choices=AgreementType.choices, db_index=True, )
    status = models.CharField( max_length=20, choices=AgreementStatus.choices, default=AgreementStatus.ACTIVE, db_index=True, )

    vendor = models.CharField( max_length=255, db_index=True, )

    reference_number = models.CharField( max_length=100, blank=True, )
    start_date = models.DateField()

    expiry_date = models.DateField( null=True, blank=True, )

    renewal_date = models.DateField( null=True, blank=True, )

    auto_renew = models.BooleanField(default=False)

    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField( max_length=10, default="USD", )

    notes = models.TextField(blank=True)

    # Management ownership
    managing_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_agreements",
    )

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["agreement_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vendor"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(expiry_date__isnull=True)
                    |
                    Q(expiry_date__gte=models.F("start_date"))
                ),
                name="agreement_expiry_after_start",
            ),

            models.CheckConstraint(
                condition=(
                    Q(renewal_date__isnull=True)
                    |
                    Q(expiry_date__isnull=True)
                    |
                    Q(renewal_date__lte=models.F("expiry_date"))
                ),
                name="agreement_renewal_before_expiry",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False

        from django.utils.timezone import now

        return self.expiry_date < now().date()


class AgreementCoverage(PublicIDModel):
    """
    Defines organizational eligibility boundaries
    for an agreement.

    Coverage does NOT automatically enroll assets.
    It only determines whether an asset MAY
    be associated to the agreement.
    """

    PUBLIC_ID_PREFIX = "AGC"

    agreement = models.ForeignKey( AssetAgreement, on_delete=models.CASCADE, related_name="coverages", )

    scope_type = models.CharField( max_length=20, choices=CoverageScopeType.choices, db_index=True, )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_coverages",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_coverages",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_coverages",
    )

    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["scope_type"]),
            models.Index(fields=["scope_type", "department"]),
            models.Index(fields=["scope_type", "location"]),
            models.Index(fields=["scope_type", "room"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        Q(scope_type=CoverageScopeType.GLOBAL)
                        &
                        Q(department__isnull=True)
                        &
                        Q(location__isnull=True)
                        &
                        Q(room__isnull=True)
                    )
                    |
                    (
                        Q(scope_type=CoverageScopeType.DEPARTMENT)
                        &
                        Q(department__isnull=False)
                        &
                        Q(location__isnull=True)
                        &
                        Q(room__isnull=True)
                    )
                    |
                    (
                        Q(scope_type=CoverageScopeType.LOCATION)
                        &
                        Q(department__isnull=True)
                        &
                        Q(location__isnull=False)
                        &
                        Q(room__isnull=True)
                    )
                    |
                    (
                        Q(scope_type=CoverageScopeType.ROOM)
                        &
                        Q(department__isnull=True)
                        &
                        Q(location__isnull=True)
                        &
                        Q(room__isnull=False)
                    )
                ),
                name="valid_agreement_coverage_scope",
            )
        ]

    def clean(self):

        # -------------------------
        # GLOBAL conflicts
        # -------------------------

        if self.scope_type == CoverageScopeType.GLOBAL:

            if self.agreement.coverages.exclude(
                pk=self.pk
            ).exists():

                raise ValidationError(
                    "Global coverage cannot coexist with other coverages."
                )

        else:

            if self.agreement.coverages.exclude(
                pk=self.pk
            ).filter(
                scope_type=CoverageScopeType.GLOBAL
            ).exists():

                raise ValidationError(
                    "Cannot add scoped coverage when global coverage exists."
                )

        # -------------------------
        # Redundant hierarchy checks
        # -------------------------

        existing = self.agreement.coverages.exclude(
            pk=self.pk
        )

        # Department coverage supersedes locations/rooms
        if self.scope_type == CoverageScopeType.LOCATION:

            if existing.filter(
                scope_type=CoverageScopeType.DEPARTMENT,
                department=self.location.department,
            ).exists():

                raise ValidationError(
                    "Department coverage already includes this location."
                )

        if self.scope_type == CoverageScopeType.ROOM:

            if existing.filter(
                scope_type=CoverageScopeType.LOCATION,
                location=self.room.location,
            ).exists():

                raise ValidationError(
                    "Location coverage already includes this room."
                )

            if existing.filter(
                scope_type=CoverageScopeType.DEPARTMENT,
                department=self.room.location.department,
            ).exists():

                raise ValidationError(
                    "Department coverage already includes this room."
                )

        # Prevent duplicate exact scopes
        if self.scope_type == CoverageScopeType.DEPARTMENT:

            if existing.filter(
                scope_type=CoverageScopeType.DEPARTMENT,
                department=self.department,
            ).exists():

                raise ValidationError(
                    "Department already covered."
                )

        if self.scope_type == CoverageScopeType.LOCATION:

            if existing.filter(
                scope_type=CoverageScopeType.LOCATION,
                location=self.location,
            ).exists():

                raise ValidationError(
                    "Location already covered."
                )

        if self.scope_type == CoverageScopeType.ROOM:

            if existing.filter(
                scope_type=CoverageScopeType.ROOM,
                room=self.room,
            ).exists():

                raise ValidationError(
                    "Room already covered."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):

        if self.scope_type == CoverageScopeType.GLOBAL:
            return f"{self.agreement} → GLOBAL"

        if self.department:
            return f"{self.agreement} → {self.department.name}"

        if self.location:
            return f"{self.agreement} → {self.location.name}"

        if self.room:
            return f"{self.agreement} → {self.room.name}"

        return str(self.agreement)

class AssetAgreementItem(PublicIDModel):
    """
    Represents an actual asset enrolled under an agreement.

    AgreementCoverage defines ELIGIBILITY.
    AssetAgreementItem defines ACTUAL MEMBERSHIP.
    """

    PUBLIC_ID_PREFIX = "AGI"

    agreement = models.ForeignKey( AssetAgreement, on_delete=models.CASCADE, related_name="items", )

    equipment = models.ForeignKey(
        "assets.Equipment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_items",
    )

    consumable = models.ForeignKey(
        "assets.Consumable",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_items",
    )

    accessory = models.ForeignKey(
        "assets.Accessory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="agreement_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    coverage_start = models.DateField( null=True, blank=True, )

    coverage_end = models.DateField( null=True, blank=True, )

    notes = models.TextField(blank=True)

    # Historical snapshots
    asset_name_snapshot = models.CharField( max_length=150, editable=False, default="", )

    asset_serial_snapshot = models.CharField(
        max_length=150,
        editable=False,
        blank=True,
        default="",
    )

    asset_public_id_snapshot = models.CharField( max_length=50, editable=False, default="", )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["coverage_start"]),
            models.Index(fields=["coverage_end"]),
        ]

        constraints = [

            # -------------------------
            # Exactly one asset type
            # -------------------------
            models.CheckConstraint(
                condition=(
                    (
                        Q(equipment__isnull=False)
                        &
                        Q(consumable__isnull=True)
                        &
                        Q(accessory__isnull=True)
                    )
                    |
                    (
                        Q(equipment__isnull=True)
                        &
                        Q(consumable__isnull=False)
                        &
                        Q(accessory__isnull=True)
                    )
                    |
                    (
                        Q(equipment__isnull=True)
                        &
                        Q(consumable__isnull=True)
                        &
                        Q(accessory__isnull=False)
                    )
                ),
                name="agreement_item_single_asset",
            ),

            # -------------------------
            # Coverage date validity
            # -------------------------
            models.CheckConstraint(
                condition=(
                    Q(coverage_end__isnull=True)
                    |
                    Q(coverage_start__isnull=True)
                    |
                    Q(coverage_end__gte=models.F("coverage_start"))
                ),
                name="agreement_item_valid_coverage_dates",
            ),

            # -------------------------
            # Equipment quantity = 1
            # -------------------------
            models.CheckConstraint(
                condition=(
                    Q(equipment__isnull=True)
                    |
                    Q(quantity=1)
                ),
                name="equipment_agreement_quantity_one",
            ),

            # -------------------------
            # Prevent duplicate coverage
            # -------------------------
            models.UniqueConstraint(
                fields=["agreement", "equipment"],
                condition=Q(equipment__isnull=False),
                name="unique_equipment_agreement_item",
            ),

            models.UniqueConstraint(
                fields=["agreement", "consumable"],
                condition=Q(consumable__isnull=False),
                name="unique_consumable_agreement_item",
            ),

            models.UniqueConstraint(
                fields=["agreement", "accessory"],
                condition=Q(accessory__isnull=False),
                name="unique_accessory_agreement_item",
            ),
        ]

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
    def is_active(self):

        from django.utils.timezone import now

        today = now().date()

        if self.coverage_start and self.coverage_start > today:
            return False

        if self.coverage_end and self.coverage_end < today:
            return False

        return True

    def is_asset_eligible(self) -> bool:
        """
        Determines whether the asset currently
        falls within the agreement's coverage scope.
        """

        asset = self.asset

        if not asset:
            return False

        room = getattr(asset, "room", None)

        if not room:
            return False

        coverages = self.agreement.coverages.all()

        for coverage in coverages:

            if coverage.scope_type == CoverageScopeType.GLOBAL:
                return True

            if (
                coverage.scope_type
                == CoverageScopeType.DEPARTMENT
            ):
                if (
                    room.location
                    and room.location.department_id
                    == coverage.department_id
                ):
                    return True

            if (
                coverage.scope_type
                == CoverageScopeType.LOCATION
            ):
                if (
                    room.location_id
                    == coverage.location_id
                ):
                    return True

            if (
                coverage.scope_type
                == CoverageScopeType.ROOM
            ):
                if room.id == coverage.room_id:
                    return True

        return False

    def clean(self):

        asset = self.asset

        if not asset:
            return

        room = getattr(asset, "room", None)

        if not room:
            raise ValidationError(
                "Agreement assets must belong to a room."
            )

        if not self.is_asset_eligible():

            raise ValidationError(
                "Asset is outside agreement coverage."
            )

    def save(self, *args, **kwargs):

        asset = self.asset

        if asset:

            self.asset_name_snapshot = (
                asset.name or ""
            )

            self.asset_public_id_snapshot = (
                asset.public_id or ""
            )

            self.asset_serial_snapshot = (
                getattr(asset, "serial_number", "")
                or ""
            )

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        asset = self.asset

        if asset:
            return (
                f"{self.agreement} → "
                f"{asset}"
            )

        return str(self.agreement)
    
class AgreementHistory(models.Model):

    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        RENEWED = "RENEWED", "Renewed"
        EXTENDED = "EXTENDED", "Extended"
        TERMINATED = "TERMINATED", "Terminated"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        EXPIRED = "EXPIRED", "Expired"

    agreement = models.ForeignKey(
        AssetAgreement,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField( max_length=30, choices=EventType.choices, db_index=True, )

    previous_status = models.CharField( max_length=20, blank=True, )

    new_status = models.CharField( max_length=20, blank=True, )

    previous_expiry_date = models.DateField( null=True, blank=True, )

    new_expiry_date = models.DateField( null=True, blank=True, )

    previous_renewal_date = models.DateField( null=True, blank=True, )

    new_renewal_date = models.DateField( null=True, blank=True, )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agreement_history",
    )

    user_email = models.EmailField(
        null=True,
        blank=True,
        max_length=255,
    )


class AgreementItemHistory(models.Model):
    """
    Historical lifecycle events for agreement item membership.

    Currently, attachment and removal actions are
    primarily tracked through AuditLog entries.

    This model remains in place for future agreement
    item lifecycle events should additional history
    tracking be required.
    """

    class EventType(models.TextChoices):
        ATTACHED = "ATTACHED", "Attached"
        REMOVED = "REMOVED", "Removed"
        INVALIDATED = "INVALIDATED", "Invalidated"
        REINSTATED = "REINSTATED", "Reinstated"
        COVERAGE_EXPIRED = "COVERAGE_EXPIRED", "Coverage Expired"

    agreement = models.ForeignKey( AssetAgreement, on_delete=models.CASCADE, related_name="item_history", )

    agreement_item = models.ForeignKey(
        AssetAgreementItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="history",
    )

    event_type = models.CharField( max_length=30, choices=EventType.choices, db_index=True, )

    # -------------------------
    # Asset snapshots
    # -------------------------

    asset_public_id = models.CharField( max_length=50, db_index=True, )

    asset_name = models.CharField( max_length=150, )

    asset_serial = models.CharField( max_length=150, blank=True, )

    asset_type = models.CharField( max_length=30, )

    # -------------------------
    # Coverage snapshots
    # -------------------------

    coverage_start = models.DateField( null=True, blank=True, )

    coverage_end = models.DateField( null=True, blank=True, )

    # -------------------------
    # Organizational snapshots
    # -------------------------

    department_name = models.CharField( max_length=255, blank=True, )

    location_name = models.CharField( max_length=255, blank=True, )

    room_name = models.CharField( max_length=255, blank=True, )

    # -------------------------
    # Metadata
    # -------------------------

    reason = models.CharField( max_length=255, blank=True, )

    metadata = models.JSONField( null=True, blank=True, )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agreement_item_history",
    )

    user_email = models.EmailField( null=True, blank=True, max_length=255, )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["asset_public_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):

        return (
            f"{self.asset_name} → "
            f"{self.event_type}"
        )