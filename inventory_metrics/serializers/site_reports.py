
from rest_framework import serializers
from db_inventory.models import Department, Location, Room
import re #regex for sanitization


class SiteSerializer(serializers.Serializer):
    siteType = serializers.ChoiceField(choices=['department', 'location', 'room'])
    siteId = serializers.CharField()

class SiteAssetRequestSerializer(serializers.Serializer):
    site = SiteSerializer()  # nested site object
    ASSET_TYPES = ['equipment', 'component', 'consumable', 'accessory']
    EXPORT_FORMATS = ['excel', 'pdf']

    asset_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ASSET_TYPES),
        allow_empty=False
    )
    export_format = serializers.ChoiceField(choices=EXPORT_FORMATS, required=False)
    file_name = serializers.CharField(required=False, allow_blank=True)

    def validate_file_name(self, value):
        import re
        if not value:
            return "site_assets" 
        return re.sub(r'[^a-zA-Z0-9_-]', '_', value)

    def validate(self, data):
        site_data = data['site']
        siteType = site_data['siteType']
        siteId = site_data['siteId']

        model_map = {
            'department': Department,
            'location': Location,
            'room': Room
        }
        model = model_map.get(siteType)
        if not model.objects.filter(public_id=siteId).exists():
            raise serializers.ValidationError(
                f"{siteType.capitalize()} with id '{siteId}' does not exist."
            )
        return data