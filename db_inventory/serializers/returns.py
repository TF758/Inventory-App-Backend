# serializers/returns.py

from rest_framework import serializers

from db_inventory.models.asset_assignment import ReturnRequest, ReturnRequestItem


class ReturnRequestItemSerializer(serializers.ModelSerializer):

    asset_public_id = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequestItem
        fields = [
            "public_id",
            "item_type",
            "quantity",
            "asset_public_id",
            "status",   
            "verified_at",
        ]

    def get_asset_public_id(self, obj):

        if obj.item_type == "equipment":
            return obj.equipment_assignment.equipment.public_id

        if obj.item_type == "accessory":
            return obj.accessory_assignment.accessory.public_id

        if obj.item_type == "consumable":
            return obj.consumable_issue.consumable.public_id

        return None


class ReturnRequestSerializer(serializers.ModelSerializer):

    items = ReturnRequestItemSerializer(many=True)

    class Meta:
        model = ReturnRequest
        fields = [
            "public_id",
            "status",
            "notes",
            "requested_at",
            "processed_at",
            "items",
        ]