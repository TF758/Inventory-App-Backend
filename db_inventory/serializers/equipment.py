
from rest_framework import serializers
from  db_inventory.models.assets import Equipment
from db_inventory.models.site import  Room

class EquipmentSerializer(serializers.ModelSerializer):
    room_id = serializers.CharField(source='room.public_id', default=None, read_only=True)
    room_name = serializers.CharField(source='room.name', default=None, read_only=True)
    location_id = serializers.CharField(source='room.location.public_id', default=None, read_only=True)
    location_name = serializers.CharField(source='room.location.name', default=None, read_only=True)
    department_id = serializers.CharField(source='room.location.department.public_id', default=None, read_only=True)
    department_name = serializers.CharField(source='room.location.department.name', default=None, read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'public_id',
            'name',
            'brand',
            'model',
            'serial_number',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
            'department_id',
            'department_name',
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

class EquipmentBatchtWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        error_messages={
            'blank': 'Equipment name cannot be empty.',
            'max_length': 'Equipment name is too long.',
        }
    )
    brand = serializers.CharField(
        required=False,
        max_length=100,
        error_messages={
            'max_length': 'Equipment brand name is too long.',
        }
    )
    model = serializers.CharField(
        required=False,
        max_length=100,
        error_messages={
            'max_length': 'Equipment model identifier is too long.',
        }
    )
    serial_number = serializers.CharField(
        max_length=100,
        error_messages={
            'max_length': 'Equipment serial identifier is too long.',
        }
    )
    room = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,  # only for input
    )

    
    class Meta:
        model = Equipment
        fields = [
            'name',
            'brand',
            'model',
            'serial_number',
            'room',
        ]

    def validate_room(self, value):
        if not value:
            return None
        qs = Room.objects.filter(public_id=value)
        if not qs.exists():
            raise serializers.ValidationError(f"Room '{value}' does not exist.")
        if qs.count() > 1:
            raise serializers.ValidationError(
                f"Multiple rooms with public_id '{value}' exist. This should not happen."
            )
        return qs.first().public_id  
        
    def create(self, validated_data):
        room_public_id = validated_data.pop("room", None)
        instance = super().create(validated_data)
        if room_public_id:
            room_obj = Room.objects.get(public_id=room_public_id)
            instance.room = room_obj
            instance.save(update_fields=["room"])
        return instance

class EquipmentWriteSerializer(serializers.ModelSerializer):
    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        allow_null=False,
        required=True,
    )

    class Meta:
        model = Equipment
        fields = [
            "public_id",      
            "name",
            "brand",
            "model",
            "serial_number",
            "room",
        ]
        read_only_fields = ["public_id"]



class EquipmentDropdownSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for dropdowns/search.
    Returns just id + name .
    """

    class Meta:
        model = Equipment
        fields = ["name", "public_id"]

__all__ = [
    "EquipmentSerializer",
    "EquipmentWriteSerializer",
    "EquipmentDropdownSerializer",
]