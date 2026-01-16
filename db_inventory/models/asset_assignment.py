from db_inventory.models.assets import Equipment, Accessory, Consumable
from db_inventory.models.users import User
from django.db import models
from django.core.exceptions import ValidationError


class EquipmentAssignment(models.Model):
    equipment = models.OneToOneField(Equipment,on_delete=models.PROTECT,related_name="active_assignment")
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name="equipment_assignments")

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="equipment_assigned")

    notes = models.TextField(blank=True)

class AccessoryAssignment(models.Model):
    accessory = models.ForeignKey(Accessory,on_delete=models.PROTECT,related_name="assignments")
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name="accessory_assignments")

    quantity = models.PositiveIntegerField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)


class ConsumableIssue(models.Model):
    consumable = models.ForeignKey(Consumable,on_delete=models.PROTECT,related_name="issues")
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name="consumables_received")
    quantity = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    purpose = models.CharField(max_length=255, blank=True)

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
    

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name="events"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    event_type = models.CharField(max_length=20, choices=Event_Choices)
    occurred_at = models.DateTimeField(auto_now_add=True)

    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_equipment_events"
    )

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

    accessory = models.ForeignKey(Accessory,on_delete=models.PROTECT,related_name="events")

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
    EVENT_TYPE_CHOICES = (
        ("issued", "Issued"),
        ("expired", "Expired"),
        ("adjusted", "Adjusted"),
    )

    consumable = models.ForeignKey(
        Consumable,
        on_delete=models.PROTECT,
        related_name="events"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    quantity = models.PositiveIntegerField()

    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    occurred_at = models.DateTimeField(auto_now_add=True)

    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_consumable_events"
    )

    notes = models.TextField(blank=True)