from rest_framework import serializers
from .departments import DepartmentNameSerializer, DepartmentReadSerializer
from ..models import * 



class LocationFullSerializer(serializers.ModelSerializer):
    department =serializers.PrimaryKeyRelatedField(queryset = Department.objects.all())
    department_detail = DepartmentNameSerializer(source = "department", read_only= True)

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department', 'department_detail']



class LocationNameShortSerializer(serializers.ModelSerializer):
    department = DepartmentNameSerializer()

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department']


class LocationRoomSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = Room
        fields = ['location', 'id', 'name']


class LocationUserLightSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    user_email = serializers.EmailField(source='user.email')
    user_fname = serializers.CharField(source='user.fname')
    user_lname = serializers.CharField(source='user.lname')

    room_id = serializers.IntegerField(source='room.id')
    room_name = serializers.CharField(source='room.name')

    class Meta:
        model = UserLocation
        fields = [
            'id',
            'user_id', 'user_email', 'user_fname', 'user_lname',
            'room_id', 'room_name', 
        ]


class LocationEquipmentSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name')
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = Equipment
        fields = ['id', 'name',  'identifier', 'room', 'room_name']


class LocationConsumableSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name')
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = Consumable
        fields = ['id', 'name', 'quantity', 'room', 'room_name']


class LocationAccessorySerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name')
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = Accessory
        fields = ['id', 'name', 'serial_number', 'quantity', 'room', 'room_name']


class LocationNameSerializer(serializers.ModelSerializer):
    department = DepartmentReadSerializer()

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department']


class LocationReadSerializer(serializers.ModelSerializer):
    department = DepartmentReadSerializer()

    class Meta:
        model = Location
        fields = ['id', 'name', 'department']


class LocationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['name', 'department']


__all__ = [
    "LocationFullSerializer",
    "LocationNameShortSerializer",
    "LocationRoomSerializer",
    "LocationUserLightSerializer",
    "LocationEquipmentSerializer",
    "LocationConsumableSerializer",
    "LocationAccessorySerializer",
    "LocationNameSerializer",
    "LocationReadSerializer",
    "LocationWriteSerializer",
]