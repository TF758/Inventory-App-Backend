from rest_framework import serializers

from db_inventory.models.assets import Consumable
from db_inventory.models.site import Location, Room


 
 # Write Serializer
class ConsumableWriteSerializer(serializers.ModelSerializer):
    room = serializers.SlugRelatedField( slug_field="public_id", queryset=Room.objects.all(), required=True, allow_null=False, )

    class Meta:
        model = Consumable
        fields = (
            "name",
            "quantity",
            "low_stock_threshold",
            "description",
            "room",
        )

    # ---------- Field-level validation ----------

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Consumable name cannot be empty.")
        return value

    def validate_description(self, value: str) -> str:
        if value is None:
            return ""
        value = value.strip()
        if len(value) > 255:
            raise serializers.ValidationError("Description is too long.")
        return value

    def validate_quantity(self, value: int) -> int:
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")

        if value > 100_000:
            raise serializers.ValidationError("Quantity value is unreasonably large.")

        return value

    def validate_low_stock_threshold(self, value: int) -> int:
        if value < 0:
            raise serializers.ValidationError( "Low stock threshold cannot be negative." )
        if value > 100_000:
            raise serializers.ValidationError( "Low stock threshold is unreasonably large." )
        return value

    # ---------- Object-level validation ----------

    def validate(self, attrs):
        # Require room on create
        if not self.instance and not attrs.get("room"):
            raise serializers.ValidationError({ "room": "Room is required." })

        quantity = attrs.get( "quantity", self.instance.quantity if self.instance else None )
        threshold = attrs.get( "low_stock_threshold", self.instance.low_stock_threshold if self.instance else None )

        if (
            quantity is not None
            and threshold is not None
            and threshold > quantity
        ):
            raise serializers.ValidationError({
                "low_stock_threshold": (
                    "Low stock threshold cannot exceed current quantity." ) })

        return attrs

class ConsumableAreaReaSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    room_id = serializers.CharField(source='room.public_id', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)

    location_id = serializers.CharField(source='room.location.public_id', read_only=True)
    location_name = serializers.CharField(source='room.location.name', read_only=True)

    department_id = serializers.CharField(source='room.location.department.public_id', read_only=True)
    department_name = serializers.CharField(source='room.location.department.name', read_only=True)

    class Meta:
        model = Consumable
        fields = [
            'public_id',
            'name',
            'quantity',
            "low_stock_threshold",
            "is_low_stock",
            'description',
            'room_id',
            'room_name',
            'location_id',
            'location_name',
            'department_id',
            'department_name'
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

class ConsumableBatchWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        error_messages={
            'blank': 'Consumable name cannot be empty.',
            'max_length': 'Consumable name is too long.',
        }
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
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
        model = Consumable
        fields = [
            'name',
            'description',
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
    'ConsumableWriteSerializer',
    'ConsumableAreaReaSerializer',
    'ConsumableBatchWriteSerializer',
]