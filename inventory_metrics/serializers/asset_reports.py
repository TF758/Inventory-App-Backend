
from rest_framework import serializers

class AssetHistoryReportRequestSerializer(serializers.Serializer):

    ASSET_TYPE_CHOICES = [
        "equipment",
        "accessory",
        "consumable",
    ]

    asset_identifier = serializers.CharField( help_text="Public ID of the asset (EQ / AC / CON)" )

    asset_type = serializers.ChoiceField( choices=ASSET_TYPE_CHOICES, help_text="Type of asset being queried" )
    start_date = serializers.DateField( required=False, help_text="Optional start date for timeline filtering" )

    end_date = serializers.DateField( required=False, help_text="Optional end date for timeline filtering" )

    def validate_asset_identifier(self, value):
        """
        Basic sanitation. Do NOT leak whether the asset exists here.
        Existence checks belong in the view.
        """
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Invalid asset identifier."
            )

        return value

    def validate(self, data):
        """
        Validate start/end date relationship.
        """
        start = data.get("start_date")
        end = data.get("end_date")

        if start and end and start > end:
            raise serializers.ValidationError(
                {"end_date": "End date must be greater than or equal to start date."}
            )

        return data