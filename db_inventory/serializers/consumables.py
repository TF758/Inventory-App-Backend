from rest_framework import serializers

from ..models import Consumable, Location
from .locations import LocationFullSerializer
from .rooms import RoomNameSerializer

class ConsumableSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationFullSerializer(source="location", read_only=True)

    class Meta:
        model = Consumable
        fields = ['public_id', 'name', 'quantity', 'description', "location","location_detail" ]
 
 # Write Serializer
class ConsumableWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumable
        fields = [
            'public_id',
            'name',
            'quantity',
            'description',
            'room',
        ]

# Read Serializer
class ConsumableReadSerializer(serializers.ModelSerializer):
    room = RoomNameSerializer()

    class Meta:
        model = Consumable
        fields = [
            'public_id',
            'name',
            'quantity',
            'description',
            'room',
        ]

class ConsumableLocationReadSerializer(serializers.ModelSerializer):
    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')

    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    department_id = serializers.CharField(source='room.location.department.public_id')
    department_name = serializers.CharField(source='room.location.department.name')

    class Meta:
        model = Consumable
        fields = [
            'public_id',
            'name',
            'quantity',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
            'department_id',
            'department_name'
        ]


__all__ = [
    'ConsumableSerializer',
    'ConsumableWriteSerializer',
    'ConsumableReadSerializer',
    'ConsumableLocationReadSerializer',
]