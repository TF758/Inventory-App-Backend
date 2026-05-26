from rest_framework import serializers
from agreements.models.agreements import AgreementCoverage, AssetAgreement, CoverageScopeType
from sites.models.sites import Department, Location, Room
from django.core.exceptions import (
    ValidationError as DjangoValidationError
)

class AgreementCoverageSerializer(serializers.ModelSerializer):

    department = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    room = serializers.SerializerMethodField()

    class Meta:
        model = AgreementCoverage

        fields = [
            "public_id",
            "scope_type",
            "department",
            "location",
            "room",
            "notes",
        ]

    def get_department(self, obj):

        if not obj.department:
            return None

        return {
            "public_id": obj.department.public_id,
            "name": obj.department.name,
        }

    def get_location(self, obj):

        if not obj.location:
            return None

        return {
            "public_id": obj.location.public_id,
            "name": obj.location.name,
        }

    def get_room(self, obj):

        if not obj.room:
            return None

        return {
            "public_id": obj.room.public_id,
            "name": obj.room.name,
        }


class AgreementCoverageWriteSerializer( serializers.ModelSerializer ):

    agreement = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=AssetAgreement.objects.all(),
    )

    department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )

    location = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
    )

    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:

        model = AgreementCoverage

        fields = [
            "agreement",
            "scope_type",
            "department",
            "location",
            "room",
            "notes",
        ]

    def create(self, validated_data):

        try:
            return super().create(
                validated_data
            )
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                e.message_dict
                if hasattr(e, "message_dict")
                else {
                    "non_field_errors":
                    e.messages
                }
            )

    def update( self, instance, validated_data, ):

        for attr, value in validated_data.items():

            setattr(
                instance,
                attr,
                value,
            )

        try:

            instance.save()

        except DjangoValidationError as e:

            raise serializers.ValidationError(
                e.message_dict
                if hasattr(e, "message_dict")
                else {
                    "non_field_errors":
                    e.messages
                }
            )

        return instance
        
    def validate(self, attrs):

        scope_type = attrs.get("scope_type")

        department = attrs.get("department")
        location = attrs.get("location")
        room = attrs.get("room")

        # -------------------------
        # GLOBAL
        # -------------------------

        if scope_type == CoverageScopeType.GLOBAL:

            if any([department, location, room]):

                raise serializers.ValidationError(
                    "Global coverage cannot define department, location, or room."
                )

        # -------------------------
        # DEPARTMENT
        # -------------------------

        elif scope_type == CoverageScopeType.DEPARTMENT:

            if not department:

                raise serializers.ValidationError(
                    "Department coverage requires a department."
                )

            if location or room:

                raise serializers.ValidationError(
                    "Department coverage cannot define location or room."
                )

        # -------------------------
        # LOCATION
        # -------------------------

        elif scope_type == CoverageScopeType.LOCATION:

            if not location:

                raise serializers.ValidationError(
                    "Location coverage requires a location."
                )

            if department or room:

                raise serializers.ValidationError(
                    "Location coverage cannot define department or room."
                )

        # -------------------------
        # ROOM
        # -------------------------

        elif scope_type == CoverageScopeType.ROOM:

            if not room:

                raise serializers.ValidationError(
                    "Room coverage requires a room."
                )

            if department or location:

                raise serializers.ValidationError(
                    "Room coverage cannot define department or location."
                )

        return attrs