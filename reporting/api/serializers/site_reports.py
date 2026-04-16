
from rest_framework import serializers
from sites.models.sites import Department, Location, Room
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

class SiteAuditLogRequestSerializer(serializers.Serializer):
    site = serializers.DictField()
    audit_period_days = serializers.IntegerField( default=30, required=False, )

    ALLOWED_SITE_TYPES = {"department", "location", "room"}
    ALLOWED_PERIODS = {30, 60, 90, 120}

    def validate_site(self, value):
        site_type = value.get("siteType")
        site_id = value.get("siteId")

        if not site_type:
            raise serializers.ValidationError("siteType is required.")

        if site_type not in self.ALLOWED_SITE_TYPES:
            raise serializers.ValidationError(
                "Invalid siteType. Must be one of: department, location, room."
            )

        if not site_id:
            raise serializers.ValidationError("siteId is required.")

        return {
            "siteType": site_type,
            "siteId": site_id,
        }

    def validate_audit_period_days(self, value):
        if value not in self.ALLOWED_PERIODS:
            raise serializers.ValidationError(
                "Invalid audit_period_days. Allowed values: 30, 60, 90, 120."
            )
        return value

    def validate(self, attrs):
        # normalize shape for ReportJob.params
        attrs["site"] = attrs["site"]
        attrs["audit_period_days"] = attrs.get("audit_period_days", 30)
        return attrs