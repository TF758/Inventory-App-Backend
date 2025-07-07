from rest_framework import serializers
from .models import User, Department, Location, Equipment, Component, Accessory, UserDepartment, Consumable

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
             'email', 'fname', 'lname', 'job_title',]
        
        # read_only_fields = ['id']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [ 'name', 'description']
        # read_only_fields = ['id']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [ 'address1', 'address2', 'city', 'country']
        # read_only_fields = ['id']

class UserDepartmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = UserDepartment
        fields = ['id', 'user', 'department', 'date_joined']
        read_only_fields = ['id', 'user', 'department']

class EquipmentSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    location = LocationSerializer(read_only=True)

    identifier = serializers.CharField(read_only=True)

    class Meta:
        model = Equipment
        fields = [ 'identifier', 'name', 'brand', 'model', 'serial_number', 'department', 'location']
        read_only_fields = [ 'department', 'location', 'identifier']

class ComponentSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)

    identifier = serializers.CharField(read_only=True)

    class Meta:
        model = Component
        fields = [ 'identifier','name', 'brand', 'model', 'serial_number', 'equipment']
        read_only_fields = [ 'equipment' , 'identifier']


class ComponentQuantitySerializer(serializers.ModelSerializer):
    component = ComponentSerializer(read_only=True)

    class Meta:
        model = Component
        fields = ['id', 'name', 'quantity']
        read_only_fields = ['id']

class AccessorySerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = Accessory
        fields = ['id', 'name', 'serial_number', 'department']
        read_only_fields = ['id', 'department']

class ConsumableSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = Consumable
        fields = ['id', 'name', 'description', 'location', 'department' ]
        read_only_fields = ['id', 'location', 'department']

class ConsumableQuantitySerializer(serializers.ModelSerializer):
    consumable = ConsumableSerializer(read_only=True)

    class Meta:
        model = Consumable
        fields = ['id', 'name', 'quantity']
        read_only_fields = ['id']

class UserDepartmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = UserDepartment
        fields = ['id', 'user', 'department', 'date_joined']
        read_only_fields = ['id', 'user', 'department']