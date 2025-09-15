from rest_framework import serializers
from .rooms import RoomNameSerializer
from ..models import User, UserLocation

class UserPrivateSerializer(serializers.ModelSerializer):
    active_role = serializers.CharField(source='active_role.get_role_id', read_only=True)

    class Meta:
        model = User
        fields = [
           'public_id',  'email', 'fname', 'lname', 'job_title', 'last_login', 'is_active' ,'active_role']
        
        ordering = ['-id']
        

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
]