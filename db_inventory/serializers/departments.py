from rest_framework import serializers
from ..models import * 




class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['public_id', 'name', 'description' ,'img_link']


class DepartmentNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = [ 'public_id', 'name']


class DepartmentReadSerializer(serializers.ModelSerializer):

    """Returns general area on a department """
    class Meta:
        model = Department
        fields = ['public_id', 'name', 'description']



class DepartmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['name', 'description' ,'img_link']


class DepartmentUserLightSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.public_id')
    user_email = serializers.EmailField(source='user.email')
    user_fname = serializers.CharField(source='user.fname')
    user_lname = serializers.CharField(source='user.lname')

    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')

    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    department_id = serializers.CharField(source='room.location.department.public_id')
    department_name = serializers.CharField(source='room.location.department.name')

    class Meta:
        model = UserLocation
        fields = [
            'id',
            'user_id', 'user_email', 'user_fname', 'user_lname',
            'room_id', 'room_name',
            'location_id', 'location_name',
            'department_id', 'department_name',
        ]


class DepartmentLocationsLightSerializer(serializers.ModelSerializer):
    room_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = ['public_id', 'name', 'room_count']

class DepartmentEquipmentSerializer(serializers.ModelSerializer):
    
    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')
    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    class Meta:
        model = Equipment
        fields = [
            'public_id',
            'name',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
        ]

class DepartmentConsumableSerializer(serializers.ModelSerializer):
    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')
    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

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
        ]

class DepartmentAccessorySerializer(serializers.ModelSerializer):
    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')
    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    class Meta:
        model = Accessory
        fields = [
            'public_id',
            'name',
            'quantity',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
        ]

class DepartmentComponentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.CharField(source='equipment.public_id')
    equipment_name = serializers.CharField(source='equipment.name')

    class Meta:
        model = Component
        fields = [
            'public_id',
            'name',
            'brand',
            'quantity',
            'equipment_id',
            'equipment_name',
        ]

__all__ = [
    "DepartmentSerializer",
    "DepartmentNameSerializer",
    "DepartmentReadSerializer",
    "DepartmentWriteSerializer",
    "DepartmentUserLightSerializer",
    "DepartmentLocationsLightSerializer",
    "DepartmentEquipmentSerializer",
    "DepartmentConsumableSerializer",
    "DepartmentAccessorySerializer",
    "DepartmentComponentSerializer"
]