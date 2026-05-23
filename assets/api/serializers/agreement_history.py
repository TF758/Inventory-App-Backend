from rest_framework import serializers

from assets.models.agreements import AgreementHistory, AgreementItemHistory




class AgreementHistorySerializer(serializers.ModelSerializer):

    agreement = serializers.SerializerMethodField()

    user = serializers.SerializerMethodField()

    class Meta:
        model = AgreementHistory

        fields = [
            "id",
            "agreement",
            "event_type",
            "previous_status",
            "new_status",
            "previous_expiry_date",
            "new_expiry_date",
            "previous_renewal_date",
            "new_renewal_date",
            "notes",
            "created_at",
            "user",
            "user_email",
        ]

    def get_agreement(self, obj):

        if not obj.agreement:
            return None

        return {
            "public_id": obj.agreement.public_id,
            "name": obj.agreement.name,
        }

    def get_user(self, obj):

        if not obj.user:
            return None

        full_name = (
            obj.user.get_full_name()
            if hasattr(obj.user, "get_full_name")
            else str(obj.user)
        )

        return {
            "id": obj.user.id,
            "name": full_name,
            "email": obj.user.email,
        }


class AgreementItemHistorySerializer(serializers.ModelSerializer):

    agreement = serializers.SerializerMethodField()

    agreement_item = serializers.SerializerMethodField()

    user = serializers.SerializerMethodField()

    class Meta:
        model = AgreementItemHistory

        fields = [
            "id",
            "agreement",
            "agreement_item",
            "event_type",
            "asset_public_id",
            "asset_name",
            "asset_serial",
            "asset_type",
            "coverage_start",
            "coverage_end",
            "department_name",
            "location_name",
            "room_name",
            "reason",
            "metadata",
            "created_at",
            "user",
            "user_email",
        ]

    def get_agreement(self, obj):

        if not obj.agreement:
            return None

        return {
            "public_id": obj.agreement.public_id,
            "name": obj.agreement.name,
        }

    def get_agreement_item(self, obj):

        if not obj.agreement_item:
            return None

        return {
            "public_id": obj.agreement_item.public_id,
        }

    def get_user(self, obj):

        if not obj.user:
            return None

        full_name = (
            obj.user.get_full_name()
            if hasattr(obj.user, "get_full_name")
            else str(obj.user)
        )

        return {
            "id": obj.user.id,
            "name": full_name,
            "email": obj.user.email,
        }