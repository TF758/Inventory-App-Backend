
from rest_framework import serializers
from db_inventory.models import Department, Location, Room
import re #regex for sanitization


class SiteAssetRequestSerializer(serializers.Serializer):
    SITE_TYPES = ['department', 'location', 'room']
    ASSET_TYPES = ['equipment', 'component', 'consumable', 'accessory']
    EXPORT_FORMATS = ['excel', 'pdf']  # optional

    site_type = serializers.ChoiceField(choices=SITE_TYPES)
    site_id = serializers.CharField()
    asset_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ASSET_TYPES),
        allow_empty=False
    )
    export_format = serializers.ChoiceField(choices=EXPORT_FORMATS, required=False)
    file_name = serializers.CharField(required=False, allow_blank=True)

    def validate_site_id(self, value):
        return value

    def validate_file_name(self, value):
        """
        Sanitize the file name: remove invalid characters and replace spaces with underscores.
        """
        if not value:
            return "site_assets" 
        # Keep only letters, numbers, underscores, and dashes
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', value)
        return sanitized

    def validate(self, data):
        site_type = data['site_type']
        site_id = data['site_id']

        model_map = {
            'department': Department,
            'location': Location,
            'room': Room
        }
        model = model_map.get(site_type)
        if not model.objects.filter(public_id=site_id).exists():
            raise serializers.ValidationError(
                f"{site_type.capitalize()} with id '{site_id}' does not exist."
            )
        
        return data
