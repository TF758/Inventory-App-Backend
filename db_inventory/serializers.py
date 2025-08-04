from rest_framework import serializers
from .models import User, Department, Location, Equipment, Component, Accessory, UserLocation, Consumable, Room

class UserSerializerPrivate(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
           'id',  'email', 'fname', 'lname', 'job_title', 'last_login', 'is_active' ,'role']
        
        ordering = ['-id']
        

class UserSerializerPublic(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email', 'fname', 'lname', 'job_title']
        
        ordering = ['-id']
        

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']


class DepartmentNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = [ 'name']


class DepartmentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']


class DepartmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['name', 'description']

class LocationFullSerializer(serializers.ModelSerializer):
    department =serializers.PrimaryKeyRelatedField(queryset = Department.objects.all())
    department_detail = DepartmentNameSerializer(source = "department", read_only= True)

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department', 'department_detail']

class LocationNameSerializer(serializers.ModelSerializer):
    department =serializers.PrimaryKeyRelatedField(queryset = Department.objects.all())
    department_detail = DepartmentNameSerializer(source = "department", read_only= True)

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'department', 'department_detail']

class LocationNameSerializer(serializers.ModelSerializer):
    department = DepartmentNameSerializer()

    class Meta:
        model = Location
        fields = [ 'name', 'department']


class LocationReadSerializer(serializers.ModelSerializer):
    department = DepartmentNameSerializer()

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
    location = LocationNameSerializer()

    class Meta:
        model = Room
        fields = [ 'name', 'location']

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
    department = DepartmentNameSerializer()

    class Meta:
        model = UserLocation
        fields = ['id', 'user', 'location', 'date_joined']



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
          
            'identifier',
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