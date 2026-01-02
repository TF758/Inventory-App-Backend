from db_inventory.models.assets import Equipment, Accessory, Consumable
from db_inventory.models.users import User
from django.db import models


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

class AccessoryEvent(models.Model):
    EVENT_TYPE_CHOICES = (
        ("assigned", "Assigned"),
        ("returned", "Returned"),
        ("lost", "Lost"),
        ("damaged", "Damaged"),
    )

    accessory = models.ForeignKey(
        Accessory,
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
        related_name="reported_accessory_events"
    )

    notes = models.TextField(blank=True)

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