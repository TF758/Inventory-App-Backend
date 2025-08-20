from rest_framework import serializers

from ..models import Consumable, Location
from .locations import LocationFullSerializer
from .rooms import RoomNameSerializer

class ConsumableSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationFullSerializer(source="location", read_only=True)

    class Meta:
        model = Consumable
        fields = ['id', 'name', 'quantity', 'description', "location","location_detail" ]
 
 # Write Serializer
class ConsumableWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumable
        fields = [
            'id',
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
            'id',
            'name',
            'quantity',
            'description',
            'room',
        ]

__all__ = [
    'ConsumableSerializer',
    'ConsumableWriteSerializer',
    'ConsumableReadSerializer',
]