from rest_framework import serializers
from ..models import * 




class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['public_id', 'name', 'description' ,'img_link']


class DepartmentListSerializer(serializers.ModelSerializer):

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



class DepartmentComponentSerializer(serializers.ModelSerializer):
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
            room = obj.equipment.room
            location = room.location


            parts = []
            if location:
                parts.append(location.name)
            if room:
                parts.append(room.name)

            return " / ".join(parts)  # e.g. "IT Dept / Main Campus / Server Room 1"
        return None

__all__ = [
    "DepartmentSerializer",
    "DepartmentListSerializer",
    "DepartmentReadSerializer",
    "DepartmentWriteSerializer",
    "DepartmentUserLightSerializer",
    "DepartmentLocationsLightSerializer",
    "DepartmentComponentSerializer"
]