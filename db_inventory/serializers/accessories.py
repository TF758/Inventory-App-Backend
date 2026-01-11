from rest_framework import serializers
from db_inventory.models.site import Location, Room
from db_inventory.models.assets import Accessory
from db_inventory.serializers.locations import LocationFullSerializer
from db_inventory.serializers.rooms import RoomNameSerializer
from rest_framework.validators import UniqueValidator


# Write Serializer
class AccessoryWriteSerializer(serializers.ModelSerializer):
    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        required=True,
    )

    serial_number = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        validators=[
            UniqueValidator(
                queryset=Accessory.objects.all(),
                message="Accessory with this serial number already exists."
            )
        ],
    )

    class Meta:
        model = Accessory
        fields = ("name", "serial_number", "quantity", "room")

    # ---------- Field-level validation ----------

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Accessory name cannot be empty.")
        return value

    def validate_serial_number(self, value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    def validate_quantity(self, value: int) -> int:
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        if value > 100_000:
            raise serializers.ValidationError("Quantity value is unreasonably large.")
        return value

    # ---------- Object-level validation ----------

    def validate(self, attrs):
        # Require room only on create
        if not self.instance and not attrs.get("room"):
            raise serializers.ValidationError({"room": "Room is required."})
        return attrs
    
class AccessoryFullSerializer(serializers.ModelSerializer):
    available_quantity = serializers.SerializerMethodField()

    room_id = serializers.CharField(source='room.public_id', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)

    location_id = serializers.CharField(source='room.location.public_id', read_only=True)
    location_name = serializers.CharField(source='room.location.name', read_only=True)

    department_id = serializers.CharField(source='room.location.department.public_id', read_only=True)
    department_name = serializers.CharField(source='room.location.department.name', read_only=True)

    class Meta:
        model = Accessory
        fields = [
            'public_id',
            'name',
            'serial_number',
            'quantity',
            'available_quantity',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
            'department_id',
            'department_name'
        ]

    def get_available_quantity(self, obj):
        return obj.available_quantity

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


class AccessoryBatchWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        error_messages={
            'blank': 'Accessory name cannot be empty.',
            'max_length': 'Accessory name is too long.',
        }
    )
    serial_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            'max_length': 'Accessory serial number is too long.',
        }
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=0,
        error_messages={
            'invalid': 'Quantity must be an integer.',
            'min_value': 'Quantity cannot be negative.'
        }
    )
    room = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,
    )

    class Meta:
        model = Accessory
        fields = [
            'name',
            'serial_number',
            'quantity',
            'room',
        ]

    def validate_room(self, value):
        if not value:
            return None
        qs = Room.objects.filter(public_id=value)
        if not qs.exists():
            raise serializers.ValidationError(f"Room '{value}' does not exist.")
        return qs.first().public_id

    def create(self, validated_data):
        room_public_id = validated_data.pop("room", None)
        instance = super().create(validated_data)
        if room_public_id:
            instance.room = Room.objects.get(public_id=room_public_id)
            instance.save(update_fields=["room"])
        return instance



__all__ = [
    'AccessoryWriteSerializer',
    'AccessoryFullSerializer',
    'AccessoryBatchWriteSerializer'
]