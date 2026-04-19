from assets.models.assets import Equipment, Accessory, Consumable
from users.models.users import User
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, F

from core.models.base import PublicIDModel
from sites.models.sites import Room


class EquipmentAssignment(models.Model):
    equipment = models.OneToOneField(Equipment,on_delete=models.CASCADE,related_name="active_assignment")
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name="equipment_assignments")

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="equipment_assigned")

    notes = models.TextField(blank=True)

class AccessoryAssignment(models.Model):
    accessory = models.ForeignKey(Accessory,on_delete=models.CASCADE,related_name="assignments")
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name="accessory_assignments")

    quantity = models.PositiveIntegerField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)


class ConsumableIssue(models.Model):
    consumable = models.ForeignKey(Consumable,on_delete=models.CASCADE,related_name="issues",)
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name="consumable_assignments",)
    quantity = models.PositiveIntegerField(help_text="Remaining quantity currently held by the user")
    # For audit/reference only 
    issued_quantity = models.PositiveIntegerField(help_text="Original quantity issued in this batch")
    assigned_at = models.DateTimeField(auto_now_add=True,help_text="When consumables were issued to the user")
    returned_at = models.DateTimeField(null=True,blank=True,help_text="Set when all remaining quantity is returned or consumed")
    assigned_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="assigned_consumables",)
    purpose = models.CharField(max_length=255,blank=True,)

    class Meta:
        indexes = [
            models.Index(fields=["consumable", "user"]),
            models.Index(fields=["user", "returned_at"]),
        ]
        constraints = [
            # Only ONE open issue per (consumable, user)
            models.UniqueConstraint(
                fields=["consumable", "user"],
                condition=Q(returned_at__isnull=True),
                name="unique_open_issue_per_user_consumable",
            ),

            # quantity must never go negative
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="consumable_issue_quantity_non_negative",
            ),

            # issued_quantity must be positive
            models.CheckConstraint(
                condition=Q(issued_quantity__gt=0),
                name="consumable_issue_issued_quantity_positive",
            ),

            # remaining quantity cannot exceed originally issued
            models.CheckConstraint(
                condition=Q(quantity__lte=F("issued_quantity")),
                name="consumable_issue_quantity_lte_issued",
            ),

            # if returned_at is set, quantity must be zero
            models.CheckConstraint(
                condition=Q(returned_at__isnull=True) | Q(quantity=0),
                name="consumable_issue_closed_has_zero_quantity",
            ),
        ]

    def clean(self):
        if self.quantity > self.issued_quantity:
            raise ValidationError(
                "quantity cannot exceed issued_quantity"
            )

    @property
    def is_active(self):
        return self.returned_at is None and self.quantity > 0

class EquipmentEvent(models.Model):
    class Event_Choices(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        RETURNED= "returned", "Returned"
        LOST= "lost", "Lost"
        DAMAGED="damaged", "Damaged"
        REPAIRED="repaired", "Repaired"
        RETIRED = "retired", "Retired"
        UNDER_REPAIR = "under_repair", "Under repair"
        CONDEMNED = "condemned", "Condemned"
        RETURN_REQUESTED = "return_requested", "Return Requested"
    

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="events" )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True )

    event_type = models.CharField(max_length=20, choices=Event_Choices)
    occurred_at = models.DateTimeField(auto_now_add=True)

    reported_by = models.ForeignKey( User, on_delete=models.SET_NULL, null=True, related_name="reported_equipment_events" )

    notes = models.TextField(blank=True)

    def __str__(self):
        return (
            f"{self.get_event_type_display()} · "
            f"{self.equipment.public_id} · "
            f"{self.occurred_at:%Y-%m-%d %H:%M}"
        )

class AccessoryEvent(models.Model):
    class EventType(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        RETURNED = "returned", "Returned"
        DAMAGED = "damaged", "Damaged"
        USED = "used", "Used" 
        LOST = "lost", "Lost"
        CONDEMNED = "condemned", "Condemned"
        RESTOCKED = "restocked", "Restocked"
        ADJUSTED = "adjusted", "Adjusted"
        RETURN_REQUESTED = "return_requested", "Return Requested"

    accessory = models.ForeignKey(Accessory,on_delete=models.CASCADE,related_name="events")

    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)

    quantity = models.PositiveIntegerField(null=True, blank=True)
    quantity_change  = models.IntegerField()

    event_type = models.CharField(max_length=20,  choices=EventType.choices,)
    occurred_at = models.DateTimeField(auto_now_add=True)

    reported_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="reported_accessory_events")

    notes = models.TextField(blank=True)

    def clean(self):
        if self.event_type in {
            self.EventType.ASSIGNED,
            self.EventType.RETURNED,
            self.EventType.RESTOCKED,
            self.EventType.CONDEMNED,
        } and self.quantity is None:
            raise ValidationError("quantity is required for this event type")

class ConsumableEvent(models.Model):
    class EventType(models.TextChoices):
        ISSUED = "issued"
        USED = "used"
        RETURNED = "returned"
        LOST = "lost"
        DAMAGED = "damaged"
        EXPIRED = "expired"
        CONDEMNED = "condemned"
        RESTOCKED = "restocked"
        ADJUSTED = "adjusted"
        RETURN_REQUESTED = "return_requested"

    consumable = models.ForeignKey(Consumable, on_delete=models.CASCADE, related_name="events")
    issue = models.ForeignKey( ConsumableIssue, null=True, blank=True, on_delete=models.SET_NULL, related_name="events" )

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    quantity = models.PositiveIntegerField()
    quantity_change = models.IntegerField()

    event_type = models.CharField(max_length=20, choices=EventType.choices)
    occurred_at = models.DateTimeField(auto_now_add=True)

    reported_by = models.ForeignKey( User, null=True, on_delete=models.SET_NULL, related_name="reported_consumable_events" )
    notes = models.TextField(blank=True)

class ReturnRequest(PublicIDModel):
    PUBLIC_ID_PREFIX = "RR"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        PARTIAL = "partial", "Partial"
        COMPLETED = "completed", "Completed"

    requester = models.ForeignKey( User, on_delete=models.CASCADE, related_name="return_requests" )
    status = models.CharField( max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True )
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="processed_return_requests"
    )

    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["requested_at"]),
        ]

class ReturnRequestItem(PublicIDModel):
    PUBLIC_ID_PREFIX = "RRI"
    PUBLIC_ID_PERMANENT = False

    class ItemType(models.TextChoices):
        EQUIPMENT = "equipment"
        ACCESSORY = "accessory"
        CONSUMABLE = "consumable"
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"

    return_request = models.ForeignKey( ReturnRequest, related_name="items", on_delete=models.CASCADE )
    item_type = models.CharField( max_length=20, choices=ItemType.choices, db_index=True )
    equipment_assignment = models.ForeignKey(EquipmentAssignment, null=True, blank=True, on_delete=models.CASCADE)
    accessory_assignment = models.ForeignKey(AccessoryAssignment, null=True, blank=True, on_delete=models.CASCADE )
    consumable_issue = models.ForeignKey( ConsumableIssue, null=True, blank=True, on_delete=models.CASCADE )
    quantity = models.PositiveIntegerField(null=True, blank=True)
    room = models.ForeignKey( Room, on_delete=models.CASCADE, db_index=True )
    status = models.CharField( max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True )
    verified_by = models.ForeignKey( User, null=True, blank=True, on_delete=models.SET_NULL )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)


    class Meta:
        indexes = [
            models.Index(fields=["item_type"]),
            models.Index(fields=["equipment_assignment"]),
            models.Index(fields=["accessory_assignment"]),
            models.Index(fields=["consumable_issue"]),
        ]