from rest_framework import serializers
from .locations import LocationNameSerializer, LocationListSerializer, LocationReadSerializer
from ..models import * 

class RoomSerializer(serializers.ModelSerializer):
    location_detail = LocationNameSerializer(source = "location", read_only = True)

    class Meta:
        model = Room
        fields = ['public_id',  'name', 'area', 'section','location', 'location_detail']


class RoomNameSerializer(serializers.ModelSerializer):
    location = LocationListSerializer()

    class Meta:
        model = Room
        fields = [ 'public_id', 'name', 'location']

class RoomListSerializer(serializers.ModelSerializer):

    """returns a list of rooms and thier ids"""
    class Meta:
        model = Room
        fields = [ 'public_id', 'name', ]

class RoomReadSerializer(serializers.ModelSerializer):
    location = LocationReadSerializer()

    class Meta:
        model = Room
        fields = ['public_id', 'name', 'area', 'section', 'location']


class RoomWriteSerializer(serializers.ModelSerializer):
    location = serializers.SlugRelatedField(
        queryset=Location.objects.all(),
        slug_field='public_id' 
    )
    class Meta:
        model = Room
        fields = ['name', 'area', 'section', 'location']

class RoomUserLightSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.public_id')
    user_email = serializers.EmailField(source='user.email')
    user_fname = serializers.CharField(source='user.fname')
    user_lname = serializers.CharField(source='user.lname')
    user_job_title = serializers.CharField(source='user.job_title')

    room_name = serializers.CharField(source='room.name')
    room_area = serializers.CharField(source='room.area')

    class Meta:
        model = UserLocation
        fields = [
            'user_id', 'user_email', 'user_fname', 'user_lname','user_job_title','room_name','room_area'
        ]

class RoomEquipmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Equipment
        fields = ['public_id', 'name', 'brand', 'model']


class RoomConsumableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumable
        fields = ['public_id', 'name', 'quantity', ]

class RoomAccessorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = ['public_id', 'name', 'serial_number', 'quantity']


class RoomComponentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.CharField(source='equipment.public_id')
    equipment_name = serializers.CharField(source='equipment.name')

    class Meta:
        model = Component
        fields = ['public_id', 'name', 'quantity', 'model', 'serial_number','equipment_id', 'equipment_name' ]


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
    "RoomListSerializer",
]