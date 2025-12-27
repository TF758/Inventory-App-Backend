from db_inventory.models.base import PublicIDModel
from django.db import models
from db_inventory.models.site import Room

class EquipmentStatus(models.TextChoices):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    LOST = "lost"
    DAMAGED = "damaged"
    UNDER_REPAIR = "under_repair"
    RETIRED = "retired"

class Equipment(PublicIDModel):
    PUBLIC_ID_PREFIX = "EQ"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, default="")
    model = models.CharField(max_length=100, blank=True, default="")
    serial_number = models.CharField(
        max_length=100, unique=True, blank=True, null=True
    )
    status = models.CharField(max_length=20,choices=EquipmentStatus.choices,default=EquipmentStatus.AVAILABLE,db_index=True, null=True)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="equipment")

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["serial_number"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.public_id}"

class Component(PublicIDModel):
    PUBLIC_ID_PREFIX = "COM"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, default="")
    model = models.CharField(max_length=100, blank=True, default="")
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    equipment = models.ForeignKey(Equipment,on_delete=models.SET_NULL,null=True,blank=True,related_name="components")

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["serial_number"]),
        ]

    def __str__(self):
        if self.equipment:
            return f"{self.name} @ {self.equipment.name}"
        return self.name

class Consumable(PublicIDModel):
    PUBLIC_ID_PREFIX = "CON"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    quantity = models.IntegerField(default=0)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="consumables")

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

class Accessory(PublicIDModel):
    PUBLIC_ID_PREFIX = "AC"

    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="accessories")

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name
