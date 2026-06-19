
from rest_framework import serializers
from assets.models.assets import Equipment, EquipmentStatus
from inventory.authorization.helpers import is_in_scope
from sites.models.sites import  Room

from django.utils import timezone

class EquipmentSerializer(serializers.ModelSerializer):
    is_assigned = serializers.SerializerMethodField()
    room_id = serializers.CharField(source='room.public_id', default=None, read_only=True)
    room_name = serializers.CharField(source='room.name', default=None, read_only=True)
    location_id = serializers.CharField(source='room.location.public_id', default=None, read_only=True)
    location_name = serializers.CharField(source='room.location.name', default=None, read_only=True)
    department_id = serializers.CharField(source='room.location.department.public_id', default=None, read_only=True)
    department_name = serializers.CharField(source='room.location.department.name', default=None, read_only=True)

    def get_is_assigned(self, obj):
        return obj.is_assigned

    class Meta:
        model = Equipment
        fields = [
            'public_id',
            'name',
            'brand',
            'model',
            'status',
            "purchase_price",
            "purchase_date",
            'is_assigned',   
            'serial_number',
            'is_deleted',
            'deleted_at',
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
            "purchase_price",
            "purchase_date",
            "status",
            "room",
        ]
        read_only_fields = ["public_id"]
    

    def validate_purchase_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Purchase price cannot be negative."
            )
        return value
    
    def validate_purchase_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError(
                "Purchase date cannot be in the future."
            )
        return value



class EquipmentDropdownSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for dropdowns/search.
    Returns just id + name .
    """

    class Meta:
        model = Equipment
        fields = ["name", "public_id"]

class EquipmentCondemnSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

class EquipmentStatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=EquipmentStatus.choices
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate_status(self, new_status):
        equipment = self.context["equipment"]
        user = self.context["request"].user

        # Condemnation uses a dedicated workflow
        if new_status == EquipmentStatus.CONDEMNED:
            raise serializers.ValidationError(
                "Equipment cannot be condemned through status updates."
            )

        # Current holder may only self-report certain statuses
        assignment = getattr(equipment, "active_assignment", None)

        if (
            assignment
            and assignment.returned_at is None
            and assignment.user_id == user.id
        ):
            allowed_statuses = {
                EquipmentStatus.OK,
                EquipmentStatus.DAMAGED,
                EquipmentStatus.UNDER_REPAIR,
            }

            if new_status not in allowed_statuses:
                raise serializers.ValidationError(
                    "You can only update the status to OK, DAMAGED, or UNDER_REPAIR."
                )

        return new_status

__all__ = [
    "EquipmentSerializer",
    "EquipmentWriteSerializer",
    "EquipmentDropdownSerializer",
    "EquipmentStatusChangeSerializer"
]