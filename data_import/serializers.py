from rest_framework import serializers

class AssetImportRequestSerializer(serializers.Serializer):
    ASSET_TYPES = ["equipment", "accessory", "consumable"]

    asset_type = serializers.ChoiceField(choices=ASSET_TYPES)
    file = serializers.FileField()

    def validate_file(self, value):
        name = value.name.lower()

        if not name.endswith(".csv"):
            raise serializers.ValidationError("Only CSV files are allowed.")

        max_size_bytes = 5 * 1024 * 1024
        if value.size > max_size_bytes:
            raise serializers.ValidationError("File exceeds the 5MB size limit.")

        return value