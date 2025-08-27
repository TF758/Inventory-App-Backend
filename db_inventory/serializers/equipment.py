
from rest_framework import serializers
from ..models import Equipment
from .rooms import RoomNameSerializer, RoomReadSerializer


class EquipmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = [
            'public_id',
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]

# Read Serializer
class EquipmentNameSerializer(serializers.ModelSerializer):
    room = RoomNameSerializer()

    class Meta:
        model = Equipment
        fields = [
            
            'public_id',
            'name',
            'room',
        ]

# Read Serializer
class EquipmentReadSerializer(serializers.ModelSerializer):
    room = RoomReadSerializer()

    class Meta:
        model = Equipment
        fields = [
            'public_id',
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]

class EquipmentDropdownSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for dropdowns/search.
    Returns just id + name .
    """

    class Meta:
        model = Equipment
        fields = ["name", "public_id"]

__all__ = [
    "EquipmentWriteSerializer",
    "EquipmentNameSerializer",
    "EquipmentReadSerializer",
    "EquipmentDropdownSerializer",
]