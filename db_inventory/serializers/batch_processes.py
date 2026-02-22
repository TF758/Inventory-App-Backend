from rest_framework import serializers
from django.contrib.auth import get_user_model

from db_inventory.models.assets import EquipmentStatus

class BatchEquipmentPublicIDsSerializer(serializers.Serializer):
    """
    Shared serializer for batch equipment actions.

    Handles:
    - ID normalization
    - Deduplication
    - Empty filtering
    """

    equipment_public_ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_equipment_public_ids(self, value):

        seen = set()
        cleaned = []

        for pid in value:
            pid = pid.strip()
            if not pid:
                continue
            if pid not in seen:
                seen.add(pid)
                cleaned.append(pid)

        if not cleaned:
            raise serializers.ValidationError(
                "No valid equipment IDs provided."
            )

        return cleaned
    
class BatchAssignEquipmentSerializer(BatchEquipmentPublicIDsSerializer):
    user_public_id = serializers.CharField()

    def validate_user_public_id(self, value):
        User = get_user_model()

        try:
            user = User.objects.get(public_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        return user

class BatchEquipmentStatusChangeSerializer(serializers.Serializer):
    equipment_public_ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )
    status = serializers.ChoiceField(choices=EquipmentStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_equipment_public_ids(self, value):
        seen = set()
        cleaned = []
        for pid in value:
            pid = pid.strip()
            if not pid:
                continue
            if pid not in seen:
                seen.add(pid)
                cleaned.append(pid)

        if not cleaned:
            raise serializers.ValidationError("No valid equipment IDs provided.")
        return cleaned

class BatchEquipmentCondemnSerializer(serializers.Serializer):
    equipment_public_ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )
    notes = serializers.CharField(required=True, allow_blank=False)

    def validate_equipment_public_ids(self, value):
        seen = set()
        cleaned = []
        for pid in value:
            pid = pid.strip()
            if not pid:
                continue
            if pid not in seen:
                seen.add(pid)
                cleaned.append(pid)

        if not cleaned:
            raise serializers.ValidationError("No valid equipment IDs provided.")
        return cleaned