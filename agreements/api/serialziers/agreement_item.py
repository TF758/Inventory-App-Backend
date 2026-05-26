
from rest_framework import serializers
from django.core.exceptions import ValidationError
from assets.models.assets import Accessory, Consumable, Equipment
from core.permissions.helpers import has_asset_custody_scope
from agreements.models.agreements import AssetAgreement, AssetAgreementItem
from inventory.agreements.services.coverage import can_attach_asset_to_agreement




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

class AssetAgreementItemSerializer( serializers.ModelSerializer ):

    agreement = serializers.CharField( source="agreement.public_id", read_only=True, )

    asset_public_id = serializers.CharField( source="asset_public_id_snapshot", read_only=True, )

    asset_type = serializers.CharField( read_only=True, )

    asset_name = serializers.CharField( source="asset_name_snapshot", read_only=True, )

    asset_serial = serializers.CharField(
        source="asset_serial_snapshot",
        read_only=True,
    )

    is_active = serializers.BooleanField(
        read_only=True,
    )

    class Meta:

        model = AssetAgreementItem

        fields = [
            "public_id",
            "agreement",
            "asset_public_id",
            "asset_type",
            "asset_name",
            "asset_serial",
            "quantity",
            "coverage_start",
            "coverage_end",
            "notes",
            "is_active",
            "created_at",
        ]

class AssetAgreementItemWriteSerializer( serializers.ModelSerializer ):

    agreement = serializers.SlugRelatedField( slug_field="public_id", queryset=AssetAgreement.objects.all() )
    asset_public_id = serializers.CharField( write_only=True )

    class Meta:

        model = AssetAgreementItem

        fields = [
            "agreement",
            "asset_public_id",
            "quantity",
            "coverage_start",
            "coverage_end",
            "notes",
        ]

    def validate(self, attrs):

        request = self.context["request"]

        asset_public_id = attrs.pop(
            "asset_public_id"
        )

        asset = resolve_asset_by_public_id(
            asset_public_id
        )

        role = request.user.active_role

        # -------------------------
        # Custody Authorization
        # -------------------------

        if not has_asset_custody_scope(
            role,
            asset,
        ):
            raise serializers.ValidationError(
                "Asset outside of your scope."
            )

        # -------------------------
        # Coverage Eligibility
        # -------------------------

        if not can_attach_asset_to_agreement(
            agreement=attrs["agreement"],
            asset=asset,
        ):
            raise serializers.ValidationError(
                (
                    "This asset does not "
                    "fall within the agreement "
                    "coverage scope."
                )
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

