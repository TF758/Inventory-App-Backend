# serializers/returns.py

from rest_framework import serializers


class EquipmentReturnRequestSerializer(serializers.Serializer):
    MAX_EQUIPMENT_PER_REQUEST = 20

    equipment = serializers.ListField( child=serializers.CharField(), allow_empty=False )

    notes = serializers.CharField( required=False, allow_blank=True )

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
    

class AccessoryReturnSerializer(serializers.Serializer):
    MAX_ASSETS_PER_REQUEST = 20

    accessories = serializers.ListField( child=serializers.DictField(), allow_empty=False )

    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_accessories(self, value):

        if len(value) > self.MAX_ASSETS_PER_REQUEST:
            raise serializers.ValidationError(
                f"You can return at most {self.MAX_ASSETS_PER_REQUEST} items per request."
            )

        ids = [item["id"] for item in value]

        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Duplicate accessory IDs detected."
            )

        return value