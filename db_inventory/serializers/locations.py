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
    room_section = serializers.CharField(source='section')

    

    class Meta:
        model = Room
        fields = ['room_id', 'room_name', 'room_section', ]

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


class LocationEquipmentSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name')
    room_id = serializers.CharField(source='room.public_id')

    class Meta:
        model = Equipment
        fields = ['public_id', 'name','brand', 'model', 'room_id', 'room_name']


class LocationConsumableSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name')
    room_id = serializers.CharField(source='room.public_id')

    class Meta:
        model = Consumable
        fields = ['public_id', 'name', 'quantity', 'room_id', 'room_name']


class LocationAccessorySerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name')
    room_id = serializers.CharField(source='room.public_id')

    class Meta:
        model = Accessory
        fields = ['public_id', 'name', 'serial_number', 'quantity', 'room_id', 'room_name']


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
    "LocationEquipmentSerializer",
    "LocationConsumableSerializer",
    "LocationAccessorySerializer",
    "LocationNameSerializer",
    "LocationReadSerializer",
    "LocationWriteSerializer",
 
]