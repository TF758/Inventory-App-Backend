from db_inventory.models.base import PublicIDModel
from django.db import models
from db_inventory.models.site import Room
from django.apps import apps

class EquipmentStatus(models.TextChoices):
    OK = "ok", "OK"
    DAMAGED = "damaged", "Damaged"
    UNDER_REPAIR = "under_repair", "Under repair"
    LOST = "lost", "Lost"
    RETIRED = "retired", "Retired"

class Equipment(PublicIDModel):
    PUBLIC_ID_PREFIX = "EQ"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, default="")
    model = models.CharField(max_length=100, blank=True, default="")
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20,choices=EquipmentStatus.choices,default=EquipmentStatus.OK,db_index=True, null=True)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="equipment")

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["serial_number"]),
        ]
 
    @property
    def is_assigned(self) -> bool:
        EquipmentAssignment = apps.get_model(
            "db_inventory", "EquipmentAssignment"
        )
        try:
            return self.active_assignment.returned_at is None
        except EquipmentAssignment.DoesNotExist:
            return False
        
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
    
    def audit_label(self) -> str:
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

    def audit_label(self) -> str:
        if self.serial_number:
            return f"{self.name} (S/N: {self.serial_number})"
        return self.name
