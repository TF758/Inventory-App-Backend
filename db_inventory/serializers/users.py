from rest_framework import serializers
from ..models import User, UserLocation, Room
from django.core.exceptions import ValidationError
from django.utils import timezone


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

    """Provide information about a user and thier location"""
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
            'public_id',
            'user_id', 'email', 'fname', 'lname', 'job_title',
            'room_id', 'room_name',
            'location_id', 'location_name',
            'department_id', 'department_name',
        ]
        read_only_fields = fields

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



class UserLocationWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating UserLocation.
    Supports assigning and unassigning a user from a room.
    """

    user_id = serializers.CharField(write_only=True)
    room_id = serializers.CharField(write_only=True, allow_null=True, required=False)

    public_id = serializers.CharField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = UserLocation
        fields = ['public_id', 'user_id', 'room_id', 'date_joined']

    def validate(self, attrs):
        user_id = attrs.get('user_id')
        room_id = attrs.get('room_id', None)

        # Validate user
        try:
            user = User.objects.get(public_id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "Invalid user public_id."})

        # Handle room validation (allow null for unassigning)
        room = None
        if room_id:
            try:
                room = Room.objects.get(public_id=room_id)
            except Room.DoesNotExist:
                raise serializers.ValidationError({"room_id": "Invalid room public_id."})

        # Enforce unique user-room constraint only if room is not null
        if room is not None:
            existing = UserLocation.objects.filter(user=user, room=room)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError("This user is already assigned to this room.")

        attrs['user'] = user
        attrs['room'] = room
        return attrs

    def create(self, validated_data):
        validated_data.pop('user_id', None)
        validated_data.pop('room_id', None)
        validated_data.setdefault('date_joined', timezone.now())
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('user_id', None)
        validated_data.pop('room_id', None)
        return super().update(instance, validated_data)

__all__ = [
    "UserWriteSerializer",
    "UserReadSerializerFull",
    "UserAreaSerializer",
    "UserLocationWriteSerializer"
]