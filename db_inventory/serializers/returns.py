# serializers/returns.py

from rest_framework import serializers

from db_inventory.models.asset_assignment import ReturnRequest, ReturnRequestItem


class EquipmentReturnRequestSerializer(serializers.Serializer):

    MAX_EQUIPMENT_PER_REQUEST = 20

    equipment = serializers.ListField( child=serializers.CharField(), allow_empty=False )

    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_equipment(self, value):

        if len(value) > self.MAX_EQUIPMENT_PER_REQUEST:
            raise serializers.ValidationError(
                f"You can return at most {self.MAX_EQUIPMENT_PER_REQUEST} equipment items per request."
            )

        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate equipment IDs detected."
            )

        return value
    
class AccessoryReturnItemSerializer(serializers.Serializer):

    accessory_public_id = serializers.CharField()  # public_id
    quantity = serializers.IntegerField(min_value=1)


class AccessoryReturnSerializer(serializers.Serializer):

    MAX_ASSETS_PER_REQUEST = 20

    accessories = AccessoryReturnItemSerializer( many=True )

    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_accessories(self, value):

        if len(value) > self.MAX_ASSETS_PER_REQUEST:
            raise serializers.ValidationError(
                f"You can return at most {self.MAX_ASSETS_PER_REQUEST} items per request."
            )

        ids = [item["accessory_public_id"] for item in value]

        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Duplicate accessory IDs detected."
            )

        return value

class ConsumableReturnItemSerializer(serializers.Serializer):

    consumable_public_id = serializers.CharField()  # public_id
    quantity = serializers.IntegerField(min_value=1)


class ConsumableReturnSerializer(serializers.Serializer):

    MAX_ASSETS_PER_REQUEST = 20

    consumables = ConsumableReturnItemSerializer(
        many=True
    )

    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_consumables(self, value):

        if len(value) > self.MAX_ASSETS_PER_REQUEST:
            raise serializers.ValidationError(
                f"You can return at most {self.MAX_ASSETS_PER_REQUEST} items per request."
            )

        ids = [item["consumable_public_id"] for item in value]

        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Duplicate consumable IDs detected."
            )

        return value

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