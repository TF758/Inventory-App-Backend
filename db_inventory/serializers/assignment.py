from rest_framework import serializers

from db_inventory.models.users import User
from db_inventory.models.assets import Equipment, EquipmentStatus
from db_inventory.models.asset_assignment import EquipmentAssignment

class EquipmentAssignmentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.CharField(source='equipment.public_id', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)

    user_id = serializers.CharField(source='user.public_id', read_only=True)
    user_name = serializers.CharField(source="user.get_full_name",read_only=True)

    assigned_by = serializers.StringRelatedField()

    class Meta:
        model = EquipmentAssignment
        fields = [
            "id",
            "equipment_id",
            "equipment_name",
            "user_id",
            "user_name",
            "assigned_at",
            "returned_at",
            "assigned_by",
            "notes",
        ]



class AssignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(public_id=attrs["user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "User not found"})

        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError({"equipment_id": "Equipment not found"})

        # State-based business rules
        if equipment.is_assigned:
            raise serializers.ValidationError(
                "This equipment is already assigned"
            )

        if equipment.status in {
            EquipmentStatus.LOST,
            EquipmentStatus.RETIRED,
        }:
            raise serializers.ValidationError(
                "This equipment cannot be assigned in its current state"
            )

        # Attach resolved objects
        attrs["user"] = user
        attrs["equipment"] = equipment
        return attrs

class UnassignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Resolve user
        try:
            user = User.objects.get(public_id=attrs["user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "User not found"})

        # Resolve equipment
        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError({"equipment_id": "Equipment not found"})

        # Must be assigned
        if not equipment.is_assigned:
            raise serializers.ValidationError(
                "This equipment is not currently assigned"
            )

        # Attach resolved objects
        attrs["equipment"] = equipment
        attrs["user"] = user
        return attrs
    
class ReassignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    from_user_id = serializers.CharField(max_length=15)
    to_user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["from_user_id"] == attrs["to_user_id"]:
            raise serializers.ValidationError(
                "from_user_id and to_user_id cannot be the same"
            )

        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError(
                {"equipment_id": "Equipment not found"}
            )

        try:
            from_user = User.objects.get(public_id=attrs["from_user_id"])
            to_user = User.objects.get(public_id=attrs["to_user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user")

        if not equipment.is_assigned:
            raise serializers.ValidationError("This equipment is not currently assigned")

        attrs.update({
            "equipment": equipment,
            "from_user": from_user,
            "to_user": to_user,
        })
        return attrs
