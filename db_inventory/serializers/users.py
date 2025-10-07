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

class UserPublicSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='fname')
    last_name = serializers.CharField(source='lname')
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'job_title']
        
        ordering = ['-id']



class UserLocationSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer()
    room = RoomNameSerializer()

    class Meta:
        model = UserLocation
        fields = ['public_id', 'user', 'room',]

__all__ = [
    "UserPrivateSerializer",
    "UserPublicSerializer",
    "UserLocationSerializer",
    "UserWriteSerializer",
    "UserReadSerializerFull",
]