from rest_framework import serializers
from .locations import LocationNameSerializer, LocationNameShortSerializer, LocationReadSerializer
from ..models import * 

class RoomSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset = Location.objects.all())
    location_detail = LocationNameSerializer(source = "location", read_only = True)

    class Meta:
        model = Room
        fields = ['id',  'name', 'area', 'section','location', 'location_detail']


class RoomNameSerializer(serializers.ModelSerializer):
    location = LocationNameShortSerializer()

    class Meta:
        model = Room
        fields = [ 'id', 'name', 'location']

class RoomReadSerializer(serializers.ModelSerializer):
    location = LocationReadSerializer()

    class Meta:
        model = Room
        fields = ['id', 'name', 'area', 'section', 'location']


class RoomWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['name', 'area', 'section', 'location']

class RoomUserLightSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    user_email = serializers.EmailField(source='user.email')
    user_fname = serializers.CharField(source='user.fname')
    user_lname = serializers.CharField(source='user.lname')
    user_job_title = serializers.CharField(source='user.job_title')

    class Meta:
        model = UserLocation
        fields = [
            'id',
            'user_id', 'user_email', 'user_fname', 'user_lname','user_job_title',
        ]

class RoomEquipmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Equipment
        fields = ['id', 'name', 'brand', 'identifier', 'model']


class RoomConsumableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumable
        fields = ['id', 'name', 'quantity', ]

class RoomAccessorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = ['id', 'name', 'serial_number', 'quantity']


class RoomComponentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.IntegerField(source='equipment.id')
    equipment_name = serializers.CharField(source='equipment.name')

    class Meta:
        model = Component
        fields = ['id', 'name', 'quantity', 'model', 'serial_number','equipment_id', 'equipment_name' ]


__all__ = [
    "RoomSerializer",
    "RoomNameSerializer",
    "RoomReadSerializer",
    "RoomWriteSerializer",
    "RoomUserLightSerializer",
    "RoomEquipmentSerializer",
    "RoomConsumableSerializer",
    "RoomAccessorySerializer",
    "RoomComponentSerializer",
]