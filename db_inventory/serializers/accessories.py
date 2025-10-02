from rest_framework import serializers
from ..models import Accessory, Location, Room
from .locations import LocationFullSerializer
from .rooms import RoomNameSerializer


class AccessorySerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationFullSerializer(source="location", read_only=True)

    
    class Meta:
        model = Accessory
        fields = ['public_id', 'name', 'serial_number', 'quantity',  "location","location_detail"   ]

# Write Serializer
class AccessoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = [
            'public_id',
            'name',
            'serial_number',
            'quantity',
            'room',
        ]

# Read Serializer
class AccessoryReadSerializer(serializers.ModelSerializer):
    room = RoomNameSerializer()

    class Meta:
        model = Accessory
        fields = [
            'public_id',
            'name',
            'serial_number',
            'quantity',
            'room',
        ]

class AccessoryFullSerializer(serializers.ModelSerializer):
    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')

    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    department_id = serializers.CharField(source='room.location.department.public_id')
    department_name = serializers.CharField(source='room.location.department.name')

    class Meta:
        model = Accessory
        fields = [
            'public_id',
            'name',
            'serial_number',
            'quantity',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
            'department_id',
            'department_name'
        ]


class AccessoryBatchWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        error_messages={
            'blank': 'Accessory name cannot be empty.',
            'max_length': 'Accessory name is too long.',
        }
    )
    serial_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            'max_length': 'Accessory serial number is too long.',
        }
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=0,
        error_messages={
            'invalid': 'Quantity must be an integer.',
            'min_value': 'Quantity cannot be negative.'
        }
    )
    room = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,
    )

    class Meta:
        model = Accessory
        fields = [
            'name',
            'serial_number',
            'quantity',
            'room',
        ]

    def validate_room(self, value):
        if not value:
            return None
        qs = Room.objects.filter(public_id=value)
        if not qs.exists():
            raise serializers.ValidationError(f"Room '{value}' does not exist.")
        return qs.first().public_id

    def create(self, validated_data):
        room_public_id = validated_data.pop("room", None)
        instance = super().create(validated_data)
        if room_public_id:
            instance.room = Room.objects.get(public_id=room_public_id)
            instance.save(update_fields=["room"])
        return instance



__all__ = [
    'AccessorySerializer',
    'AccessoryWriteSerializer',
    'AccessoryReadSerializer',
    'AccessoryFullSerializer',
    'AccessoryBatchWriteSerializer'
]