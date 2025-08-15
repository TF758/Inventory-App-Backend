from rest_framework import serializers
from .models import User, Department, Location, Equipment, Component, Accessory, UserLocation, Consumable, Room

class UserSerializerPrivate(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
           'id',  'email', 'fname', 'lname', 'job_title', 'last_login', 'is_active' ,'role']
        
        ordering = ['-id']
        

class UserSerializerPublic(serializers.ModelSerializer):
    first_name = serializers.CharField(source='fname')
    last_name = serializers.CharField(source='lname')
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'job_title']
        
        ordering = ['-id']
        

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description' ,'img_link']


class DepartmentNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = [ 'id', 'name']


class DepartmentReadSerializer(serializers.ModelSerializer):

    """Returns general area on a department """
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']



class DepartmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['name', 'description' ,'img_link']

class LocationFullSerializer(serializers.ModelSerializer):
    department =serializers.PrimaryKeyRelatedField(queryset = Department.objects.all())
    department_detail = DepartmentNameSerializer(source = "department", read_only= True)

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department', 'department_detail']


class DepartmentUserLightSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    user_email = serializers.EmailField(source='user.email')
    user_first_name = serializers.CharField(source='user.fname')
    user_last_name = serializers.CharField(source='user.lname')

    room_id = serializers.IntegerField(source='room.id')
    room_name = serializers.CharField(source='room.name')

    location_id = serializers.IntegerField(source='room.location.id')
    location_name = serializers.CharField(source='room.location.name')

    department_id = serializers.IntegerField(source='room.location.department.id')
    department_name = serializers.CharField(source='room.location.department.name')

    class Meta:
        model = UserLocation
        fields = [
            'id',
            'user_id', 'user_email', 'user_first_name', 'user_last_name',
            'room_id', 'room_name',
            'location_id', 'location_name',
            'department_id', 'department_name',
        ]

class DepartmentLocationsLightSerializer(serializers.ModelSerializer):

    room_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = [
            'id',
            'name',  'room_count',
        ]

class DepartmentEquipmentSerializer(serializers.ModelSerializer):
    
    room_id = serializers.IntegerField(source='room.id')
    room_name = serializers.CharField(source='room.name')
    location_id = serializers.IntegerField(source='room.location.id')
    location_name = serializers.CharField(source='room.location.name')

    class Meta:
        model = Equipment
        fields = [
            'id',
            'name',
            'brand',
            'identifier',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
        ]

class LocationNameSerializerShort(serializers.ModelSerializer):
    department = DepartmentNameSerializer()

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department']


class LocationRoomSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = Room
        fields = ['location', 'id', 'name']


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

class RoomSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset = Location.objects.all())
    location_detail = LocationNameSerializer(source = "location", read_only = True)

    class Meta:
        model = Room
        fields = ['id',  'name', 'area', 'section','location', 'location_detail']


class RoomNameSerializer(serializers.ModelSerializer):
    location = LocationNameSerializerShort()

    class Meta:
        model = Room
        fields = [ 'id', 'name', 'location']

class RoomReadSerializer(serializers.ModelSerializer):
    location = LocationReadSerializer()

    class Meta:
        model = Room
        fields = ['id', 'name', 'area', 'section', 'location']


class RoomWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['name', 'area', 'section', 'location']

class UserLocationSerializer(serializers.ModelSerializer):
    user = UserSerializerPublic()
    room = RoomNameSerializer()

    class Meta:
        model = UserLocation
        fields = ['id', 'user', 'room',]



class EquipmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]

# Read Serializer
class EquipmentNameSerializer(serializers.ModelSerializer):
    room = RoomNameSerializer()

    class Meta:
        model = Equipment
        fields = [
            
            'id',
            'name',
            'room',
        ]

# Read Serializer
class EquipmentReadSerializer(serializers.ModelSerializer):
    room = RoomReadSerializer()

    class Meta:
        model = Equipment
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]


    # Write Serializer
class ComponentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'quantity',
            'model',
            'serial_number',
            'equipment',
        ]

# Read Serializer
class ComponentReadSerializer(serializers.ModelSerializer):
    equipment = EquipmentNameSerializer( read_only=True)

    class Meta:
        model = Component
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'quantity',
            'model',
            'serial_number',
            'equipment',
            
        ]
  


class AccessorySerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationFullSerializer(source="location", read_only=True)

    
    class Meta:
        model = Accessory
        fields = ['id', 'name', 'serial_number', 'quantity',  "location","location_detail"   ]

# Write Serializer
class AccessoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = [
            'id',
            'name',
            'serial_number',
            'quantity',
            'room',
        ]

# Read Serializer
class AccessoryReadSerializer(serializers.ModelSerializer):
    room = RoomNameSerializer()

    class Meta:
        model = Accessory
        fields = [
            'id',
            'name',
            'serial_number',
            'quantity',
            'room',
        ]

class ConsumableSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationFullSerializer(source="location", read_only=True)

    class Meta:
        model = Consumable
        fields = ['id', 'name', 'quantity', 'description', "location","location_detail" ]
 
 # Write Serializer
class ConsumableWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumable
        fields = [
            'id',
            'name',
            'quantity',
            'description',
            'room',
        ]

# Read Serializer
class ConsumableReadSerializer(serializers.ModelSerializer):
    room = RoomNameSerializer()

    class Meta:
        model = Consumable
        fields = [
            'id',
            'name',
            'quantity',
            'description',
            'room',
        ]