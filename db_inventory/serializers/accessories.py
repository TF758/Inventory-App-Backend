from rest_framework import serializers
from ..models import Accessory, Location
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


__all__ = [
    'AccessorySerializer',
    'AccessoryWriteSerializer',
    'AccessoryReadSerializer',
    'AccessoryFullSerializer',
]