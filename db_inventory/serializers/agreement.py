
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from db_inventory.models.assets import Accessory, AssetAgreement, AssetAgreementItem, Component, Consumable, Equipment
from db_inventory.permissions.helpers import has_asset_custody_scope
from db_inventory.models.site import Department, Location, Room



def resolve_asset_by_public_id(public_id: str):
    """
    Resolve asset instance based on public_id prefix.
    """

    if not public_id:
        raise serializers.ValidationError("Asset public_id is required.")

    model_map = {
        "EQ": Equipment,
        "CON": Consumable,
        "AC": Accessory,
    }

    model = None
    for prefix, candidate_model in model_map.items():
        if public_id.startswith(prefix):
            model = candidate_model
            break

    if not model:
        raise serializers.ValidationError("Unknown asset type.")

    try:
        return model.objects.get(public_id=public_id)
    except model.DoesNotExist:
        raise serializers.ValidationError("Asset not found.")

class AssetAgreementItemSerializer(serializers.ModelSerializer):

    agreement = serializers.CharField(source="agreement.public_id", read_only=True)
    asset_public_id = serializers.CharField(source="asset.public_id", read_only=True)
    asset_type = serializers.CharField(read_only=True)

    class Meta:
        model = AssetAgreementItem
        fields = [
            "id",
            "agreement",
            "asset_public_id",
            "asset_type",
            "quantity",
        ]

class AssetAgreementItemWriteSerializer(serializers.ModelSerializer):

    agreement = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=AssetAgreement.objects.all()
    )

    asset_public_id = serializers.CharField(write_only=True)

    class Meta:
        model = AssetAgreementItem
        fields = [
            "agreement",
            "asset_public_id",
            "quantity",
        ]

    def validate(self, attrs):

        request = self.context["request"]

        asset_public_id = attrs.pop("asset_public_id")   # ← IMPORTANT
        agreement = attrs.get("agreement")

        asset = resolve_asset_by_public_id(asset_public_id)

        role = request.user.active_role

        if not has_asset_custody_scope(role, asset):
            raise serializers.ValidationError(
                "Asset outside of your scope."
            )

        asset_room = asset.room

        if not asset_room:
            raise serializers.ValidationError(
                "Asset must belong to a room."
            )

        if agreement.room and asset_room != agreement.room:
            raise serializers.ValidationError(
                "Asset outside agreement room scope."
            )

        if agreement.location and asset_room.location != agreement.location:
            raise serializers.ValidationError(
                "Asset outside agreement location scope."
            )

        if agreement.department and asset_room.location.department != agreement.department:
            raise serializers.ValidationError(
                "Asset outside agreement department scope."
            )

        attrs["asset"] = asset

        return attrs


    def create(self, validated_data):

        asset = validated_data.pop("asset")

        item = AssetAgreementItem(**validated_data)

        if isinstance(asset, Equipment):
            item.equipment = asset
        elif isinstance(asset, Consumable):
            item.consumable = asset
        elif isinstance(asset, Accessory):
            item.accessory = asset

        try:
            item.save()
        except ValidationError  as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, "message_dict") else e.messages
            )

        return item

class AssetAgreementSerializer(serializers.ModelSerializer):

    department = serializers.CharField(
        source="department.public_id",
        read_only=True
    )

    location = serializers.CharField(
        source="location.public_id",
        read_only=True
    )

    room = serializers.CharField(
        source="room.public_id",
        read_only=True
    )

    covered_assets = serializers.SerializerMethodField()

    class Meta:
        model = AssetAgreement
        fields = [
            "public_id",
            "name",
            "agreement_type",
            "vendor",
            "reference_number",
            "start_date",
            "expiry_date",
            "cost",
            "expiry_notice_days",
            "auto_renew",
            "notes",
            "department",
            "location",
            "room",
            "covered_assets",
        ]

    def get_covered_assets(self, obj):
        return [
            {
                "asset_public_id": item.asset_public_id,
                "quantity": item.quantity,
            }
            for item in obj.items.all()
        ]

class AssetAgreementWriteSerializer(serializers.ModelSerializer):

    department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True
    )

    location = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Location.objects.all(),
        required=False,
        allow_null=True
    )

    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = AssetAgreement
        fields = [
            "name",
            "agreement_type",
            "vendor",
            "reference_number",
            "start_date",
            "expiry_date",
            "cost",
            "expiry_notice_days",
            "auto_renew",
            "notes",
            "department",
            "location",
            "room",
        ]