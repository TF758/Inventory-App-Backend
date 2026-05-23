from rest_framework import serializers

from assets.models.assets import AssetAgreement
from sites.models.sites import Department



class AssetAgreementSerializer(serializers.ModelSerializer):

    managing_department = serializers.SerializerMethodField()

    is_expired = serializers.BooleanField(
        read_only=True,
    )

    item_count = serializers.SerializerMethodField()

    coverage_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetAgreement

        fields = [
            "public_id",
            "name",
            "agreement_type",
            "status",
            "vendor",
            "reference_number",
            "start_date",
            "expiry_date",
            "renewal_date",
            "auto_renew",
            "cost",
            "currency",
            "notes",
            "managing_department",
            "is_expired",
            "item_count",
            "coverage_count",
        ]

    def get_managing_department(self, obj):

        if not obj.managing_department:
            return None

        return {
            "public_id": obj.managing_department.public_id,
            "name": obj.managing_department.name,
        }

    def get_item_count(self, obj):

        return obj.items.count()

    def get_coverage_count(self, obj):

        return obj.coverages.count()


class AssetAgreementWriteSerializer(serializers.ModelSerializer):

    managing_department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = AssetAgreement

        fields = [
            "name",
            "agreement_type",
            "status",
            "vendor",
            "reference_number",
            "start_date",
            "expiry_date",
            "renewal_date",
            "auto_renew",
            "cost",
            "currency",
            "notes",
            "managing_department",
        ]