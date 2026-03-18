
from db_inventory.models.users import User
from rest_framework import serializers

from db_inventory.models.asset_assignment import AccessoryAssignment, ConsumableIssue


class SelfUserProfileSerializer(serializers.ModelSerializer):
    equipment_count = serializers.IntegerField(read_only=True)
    accessory_count = serializers.IntegerField(read_only=True)
    consumable_count = serializers.IntegerField(read_only=True)

    current_location = serializers.SerializerMethodField()
    active_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "public_id",
            "email",
            "fname",
            "lname",
            "job_title",
            "is_active",
            "last_login",
            "current_location",
            "active_role",
            "equipment_count",
            "accessory_count",
            "consumable_count",
        )

    def get_current_location(self, obj):
        ul = (
            obj.user_locations
            .select_related("room__location__department")
            .filter(is_current=True)
            .first()
        )

        if not ul or not ul.room:
            return None

        return {
            "room": ul.room.name,
            "location": ul.room.location.name,
            "department": ul.room.location.department.name,
        }

    def get_active_role(self, obj):
        role = obj.active_role
        if not role:
            return None

        if role.role == "SITE_ADMIN":
            return {
                "role": role.role,
                "scope_type": "site",
                "scope_name": "Entire Site",
            }

        if role.room:
            return {
                "role": role.role,
                "scope_type": "room",
                "scope_name": role.room.name,
            }

        if role.location:
            return {
                "role": role.role,
                "scope_type": "location",
                "scope_name": role.location.name,
            }

        if role.department:
            return {
                "role": role.role,
                "scope_type": "department",
                "scope_name": role.department.name,
            }

        return {
            "role": role.role,
            "scope_type": None,
            "scope_name": None,
        }


class SelfAssignedEquipmentSerializer(serializers.Serializer):
    """
    Serializer for equipment currently assigned to the authenticated user.
    Input model: EquipmentAssignment
    Output: flattened equipment data
    """

    public_id = serializers.CharField(source="equipment.public_id")
    name = serializers.CharField(source="equipment.name")
    brand = serializers.CharField(source="equipment.brand")
    model = serializers.CharField(source="equipment.model")
    status = serializers.CharField(source="equipment.status")

    has_pending_return_request = serializers.BooleanField(read_only=True)

    room = serializers.SerializerMethodField()

    def get_room(self, obj):
        room = obj.equipment.room
        if not room:
            return None

        return {
            "public_id": room.public_id,
            "name": room.name,
        }

class SelfAccessoryAssignmentSerializer(serializers.ModelSerializer):
    accessory_public_id = serializers.CharField( source="accessory.public_id", read_only=True, )
    accessory_name = serializers.CharField( source="accessory.name", read_only=True, )
    room_name = serializers.CharField( source="accessory.room.name", read_only=True, )
    room_public_id = serializers.CharField( source="accessory.room.public_id", read_only=True, )
    has_pending_return_request = serializers.BooleanField(read_only=True)
    pending_return_quantity = serializers.IntegerField(read_only=True)
    available_return_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = AccessoryAssignment
        fields = (
            "accessory_public_id",
            "accessory_name",
            "quantity",
            "assigned_at",
            "room_name",
            "room_public_id",
            "has_pending_return_request",
            "pending_return_quantity",
            "available_return_quantity"
        )

class SelfConsumableIssueSerializer(serializers.ModelSerializer):
    public_id = serializers.CharField( source="consumable.public_id", read_only=True, )
    name = serializers.CharField( source="consumable.name", read_only=True, )
    room_name = serializers.CharField( source="consumable.room.name", read_only=True, )
    room_public_id = serializers.CharField( source="consumable.room.public_id", read_only=True, )
    has_pending_return_request = serializers.BooleanField(read_only=True)
    pending_return_quantity = serializers.IntegerField(read_only=True)
    available_return_quantity = serializers.IntegerField(read_only=True)
    class Meta:
        model = ConsumableIssue
        fields = (
            "public_id",
            "name",
            "quantity",       
            "assigned_at",
            "room_name",
            "room_public_id",
            "purpose",
            "has_pending_return_request",
            "pending_return_quantity",
            "available_return_quantity",       
        )


class SelfAssetSerializer(serializers.Serializer):
    asset_type = serializers.CharField()
    public_id = serializers.CharField()

    name = serializers.CharField()

    brand = serializers.CharField(required=False, allow_null=True)
    model = serializers.CharField(required=False, allow_null=True)
    serial_number = serializers.CharField(required=False, allow_null=True)

    quantity = serializers.IntegerField(required=False, allow_null=True)
    available_return_quantity = serializers.IntegerField(required=False, allow_null=True)

    assigned_at = serializers.DateTimeField()

    room = serializers.CharField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_null=True)
    department = serializers.CharField(required=False, allow_null=True)

    can_return = serializers.BooleanField()
    has_pending_return_request = serializers.BooleanField(read_only=True)

class MixedAssetReturnItemSerializer(serializers.Serializer):
    asset_type = serializers.ChoiceField(
        choices=["equipment", "accessory", "consumable"]
    )
    public_id = serializers.CharField()
    quantity = serializers.IntegerField(required=False, min_value=1)

    def validate(self, data):
        if data["asset_type"] in ["accessory", "consumable"]:
            if "quantity" not in data:
                raise serializers.ValidationError(
                    f"Quantity required for {data['asset_type']}"
                )
        return data


class MixedAssetReturnSerializer(serializers.Serializer):
    items = MixedAssetReturnItemSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data["items"]:
            raise serializers.ValidationError("At least one item is required.")

        seen = set()

        for item in data["items"]:
            key = (item["asset_type"], item["public_id"])

            if key in seen:
                raise serializers.ValidationError(
                    f"Duplicate item: {item['public_id']}"
                )
            seen.add(key)

        return data