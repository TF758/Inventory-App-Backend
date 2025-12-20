from rest_framework import serializers
from db_inventory.models.site import Room,Location
from db_inventory.serializers.locations import * 

class RoomSerializer(serializers.ModelSerializer):
    location_detail = LocationNameSerializer(source = "location", read_only = True)

    class Meta:
        model = Room
        fields = ['public_id',  'name','location', 'location_detail']


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
        fields = ['public_id', 'name', 'location']


class RoomSerializer(serializers.ModelSerializer):


    class Meta:
        model = Room
        fields = ['public_id', 'name', ]



class RoomWriteSerializer(serializers.ModelSerializer):
    location = serializers.SlugRelatedField(
        queryset=Location.objects.all(),
        slug_field='public_id' 
    )
    class Meta:
        model = Room
        fields = ['name',  'location']



__all__ = [
    "RoomSerializer",
    "RoomNameSerializer",
    "RoomReadSerializer",
    "RoomWriteSerializer",
    "RoomListSerializer",
]