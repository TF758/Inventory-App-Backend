
from rest_framework import serializers
from ..models import Equipment, Room
from .rooms import RoomNameSerializer, RoomReadSerializer


class EquipmentBatchtWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        error_messages={
            'blank': 'Equipment name cannot be empty.',
            'max_length': 'Equipment name is too long.',
        }
    )
    brand = serializers.CharField(
        required=False,
        max_length=100,
        error_messages={
            'max_length': 'Equipment brand name is too long.',
        }
    )
    model = serializers.CharField(
        required=False,
        max_length=100,
        error_messages={
            'max_length': 'Equipment model identifier is too long.',
        }
    )
    serial_number = serializers.CharField(
        max_length=100,
        error_messages={
            'max_length': 'Equipment serial identifier is too long.',
        }
    )
    room = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,  # only for input
    )

    
    class Meta:
        model = Equipment
        fields = [
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]

    def validate_room(self, value):
        if not value:
            return None
        qs = Room.objects.filter(public_id=value)
        if not qs.exists():
            raise serializers.ValidationError(f"Room '{value}' does not exist.")
        if qs.count() > 1:
            raise serializers.ValidationError(
                f"Multiple rooms with public_id '{value}' exist. This should not happen."
            )
        return qs.first().public_id  # safe, returns the ID only
        
    def create(self, validated_data):
        room_public_id = validated_data.pop("room", None)
        instance = super().create(validated_data)
        if room_public_id:
            room_obj = Room.objects.get(public_id=room_public_id)
            instance.room = room_obj
            instance.save(update_fields=["room"])
        return instance

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