from rest_framework import serializers
from .departments import DepartmentListSerializer, DepartmentReadSerializer
from ..models import * 



class LocationFullSerializer(serializers.ModelSerializer):
    department_detail = DepartmentListSerializer(source = "department", read_only= True)

    class Meta:
        model = Location
        fields = [ 'public_id', 'name', 'department_detail']



class LocationListSerializer(serializers.ModelSerializer):

    """ returns a list of Locations and thier IDs"""

    class Meta:
        model = Location
        fields = [ 'public_id', 'name']


class LocationRoomSerializer(serializers.ModelSerializer):

    room_id = serializers.CharField(source='public_id')
    room_name = serializers.CharField(source='name')
 
    class Meta:
        model = Room
        fields = ['room_id', 'room_name',  ]

class LocationUserLightSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.public_id')
    user_email = serializers.EmailField(source='user.email')
    user_fname = serializers.CharField(source='user.fname')
    user_lname = serializers.CharField(source='user.lname')

    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')

    class Meta:
        model = UserLocation
        fields = [
           
            'user_id', 'user_email', 'user_fname', 'user_lname',
            'room_id', 'room_name', 
        ]


class LocationComponentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.CharField(source='equipment.public_id')
    equipment_name = serializers.CharField(source='equipment.name')

    area_id = serializers.SerializerMethodField()
    area_name = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            'public_id',
            'name',
            'brand',
            'model',
            'quantity',
            'serial_number',
            'equipment_id',
            'equipment_name',
            'area_id',
            'area_name',
        ]

    def get_area_id(self, obj):
        if obj.equipment and obj.equipment.room:
            return obj.equipment.room.public_id
        return None

    def get_area_name(self, obj):
        if obj.equipment and obj.equipment.room:
            return obj.equipment.room.name   # ✅ just the room name
        return None

class LocationNameSerializer(serializers.ModelSerializer):
    department = DepartmentReadSerializer()

    class Meta:
        model = Location
        fields = [ 'public_id', 'name', 'department']


class LocationReadSerializer(serializers.ModelSerializer):
    department = DepartmentReadSerializer()

    class Meta:
        model = Location
        fields = ['public_id', 'name', 'department']


class LocationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['name', 'department']


__all__ = [
    "LocationFullSerializer",
    "LocationListSerializer",
    "LocationRoomSerializer",
    "LocationUserLightSerializer",
    "LocationNameSerializer",
    "LocationReadSerializer",
    "LocationWriteSerializer",
    "LocationComponentSerializer"
 
]