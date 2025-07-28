from rest_framework import serializers
from .models import User, Department, Location, Equipment, Component, Accessory, UserLocation, Consumable

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


class LocationSerializer(serializers.ModelSerializer):
    department =serializers.PrimaryKeyRelatedField(queryset = Department.objects.all())
    department_detail = DepartmentNameSerializer(source = "department", read_only= True)

    class Meta:
        model = Location
        fields = [ 'id', 'name', 'room', 'area', 'section', 'department', 'department_detail']


class UserLocationSerializer(serializers.ModelSerializer):
    user = UserSerializerPublic()
    department = DepartmentNameSerializer()

    class Meta:
        model = UserLocation
        fields = ['id', 'user', 'location', 'date_joined']


class EquipmentSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationSerializer(source="location", read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'id',
            "identifier",
            "name",
            "brand",
            "model",
            "serial_number",
            "location",        
            "location_detail"   
        ]


class ComponentSerializer(serializers.ModelSerializer):
    equipment = serializers.PrimaryKeyRelatedField(queryset = Equipment.objects.all())
    equipment_detail = EquipmentSerializer(source = "equipment", read_only = True)

    class Meta:
        model = Component
        fields = [ 'id', 'identifier','name', 'brand', 'quantity', 'model', 'serial_number', 'equipment', 'equipment_detail']
  


class AccessorySerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationSerializer(source="location", read_only=True)

    
    class Meta:
        model = Accessory
        fields = ['id', 'name', 'serial_number', 'quantity',  "location","location_detail"   ]


class ConsumableSerializer(serializers.ModelSerializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    location_detail = LocationSerializer(source="location", read_only=True)

    class Meta:
        model = Consumable
        fields = ['id', 'name', 'quantity', 'description', "location","location_detail" ]
 