from rest_framework import serializers

from db_inventory.models.users import User
from db_inventory.models.assets import Equipment, EquipmentStatus
from db_inventory.models.asset_assignment import EquipmentAssignment

class AssignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Validate user exists
        try:
            user = User.objects.get(public_id=attrs["user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"user_id": "User not found"}
            )

        # Validate equipment exists
        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError(
                {"equipment_id": "Equipment not found"}
            )

        # Business rules
        if equipment.status == EquipmentStatus.ASSIGNED:
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

        # Attach resolved objects (important)
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
            raise serializers.ValidationError(
                {"user_id": "User not found"}
            )

        # Resolve equipment
        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError(
                {"equipment_id": "Equipment not found"}
            )

        # Must be assigned
        if equipment.status != EquipmentStatus.ASSIGNED:
            raise serializers.ValidationError(
                "This equipment is not currently assigned"
            )

        # Must be assigned to THIS user
        try:
            assignment = equipment.active_assignment
        except EquipmentAssignment.DoesNotExist:
            raise serializers.ValidationError(
                "No active assignment found for this equipment"
            )

        if assignment.user != user:
            raise serializers.ValidationError(
                "This equipment is not assigned to the specified user"
            )

        # Attach resolved objects
        attrs["equipment"] = equipment
        attrs["user"] = user
        attrs["assignment"] = assignment

        return attrs

