from rest_framework import serializers
from .rooms import RoomNameSerializer
from ..models import User, UserLocation

class UserPrivateSerializer(serializers.ModelSerializer):
    current_role = serializers.CharField(source='active_role.get_role_id', read_only=True)

    class Meta:
        model = User
        fields = [
           'public_id',  'email', 'fname', 'lname', 'job_title', 'last_login', 'is_active' ,'current_role']
        
        ordering = ['-id']

class UserReadSerializerFull(serializers.ModelSerializer):
    """Serilziers known information about a user"""

    current_role = serializers.CharField(source='active_role.get_role_id', read_only=True)

    class Meta:
        model = User
        fields = [
            'public_id',  'email', 'fname', 'lname', 'job_title', 'last_login', 'is_active' ,'current_role'
        ]
        read_only_fields = ('public_id', 'last_login')


class UserWriteSerializer(serializers.ModelSerializer):   
     class Meta:
        model = User
        fields = [
              'email', 'fname', 'lname', 'job_title', 'is_active' ,
        ]     

class UserAreaSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.public_id')
    email = serializers.EmailField(source='user.email')
    fname = serializers.CharField(source='user.fname')
    lname = serializers.CharField(source='user.lname')
    job_title = serializers.CharField(source ='user.job_title')

    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')

    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    department_id = serializers.CharField(source='room.location.department.public_id')
    department_name = serializers.CharField(source='room.location.department.name')

    class Meta:
        model = UserLocation
        fields = [
            'user_id', 'email', 'fname', 'lname', 'job_title',
            'room_id', 'room_name',
            'location_id', 'location_name',
            'department_id', 'department_name',
        ]


    def __init__(self, *args, **kwargs):
        exclude_room = kwargs.pop('exclude_room', False)
        exclude_location = kwargs.pop('exclude_location', False)
        exclude_department = kwargs.pop('exclude_department', False)
        super().__init__(*args, **kwargs)


        if exclude_room:
            self.fields.pop('room_id', None)
            self.fields.pop('room_name', None)
        if exclude_location:
            self.fields.pop('location_id', None)
            self.fields.pop('location_name', None)
        if exclude_department:
            self.fields.pop('department_id', None)
            self.fields.pop('department_name', None)


__all__ = [
    "UserWriteSerializer",
    "UserReadSerializerFull",
    "UserAreaSerializer",
]