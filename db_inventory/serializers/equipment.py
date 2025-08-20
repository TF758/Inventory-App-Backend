
from rest_framework import serializers
from ..models import Equipment
from .rooms import RoomNameSerializer, RoomReadSerializer


class EquipmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = [
            'id',
            'identifier',
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
            
            'id',
            'name',
            'room',
        ]

# Read Serializer
class EquipmentReadSerializer(serializers.ModelSerializer):
    room = RoomReadSerializer()

    class Meta:
        model = Equipment
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]

__all__ = [
    "EquipmentWriteSerializer",
    "EquipmentNameSerializer",
    "EquipmentReadSerializer",
]