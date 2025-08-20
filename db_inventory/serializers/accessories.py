from rest_framework import serializers
from ..models import Accessory, Location
from .locations import LocationFullSerializer
from .rooms import RoomNameSerializer


class AccessorySerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationFullSerializer(source="location", read_only=True)

    
    class Meta:
        model = Accessory
        fields = ['id', 'name', 'serial_number', 'quantity',  "location","location_detail"   ]

# Write Serializer
class AccessoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = [
            'id',
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
            'id',
            'name',
            'serial_number',
            'quantity',
            'room',
        ]


__all__ = [
    'AccessorySerializer',
    'AccessoryWriteSerializer',
    'AccessoryReadSerializer',
]