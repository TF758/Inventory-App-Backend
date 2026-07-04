# sites/api/option_serializers.py

from rest_framework import serializers

from sites.models import Department, Location, Room


class DepartmentOptionSerializer(serializers.ModelSerializer):
    value = serializers.CharField(source="public_id", read_only=True)
    label = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Department
        fields = [
            "value",
            "label",
            "public_id",
            "name",
        ]


class LocationOptionSerializer(serializers.ModelSerializer):
    value = serializers.CharField(source="public_id", read_only=True)
    label = serializers.CharField(source="name", read_only=True)
    department_id = serializers.CharField(
        source="department.public_id",
        read_only=True,
    )
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    class Meta:
        model = Location
        fields = [
            "value",
            "label",
            "public_id",
            "name",
            "department_id",
            "department_name",
        ]


class RoomOptionSerializer(serializers.ModelSerializer):
    value = serializers.CharField(source="public_id", read_only=True)
    label = serializers.CharField(source="name", read_only=True)
    location_id = serializers.CharField(
        source="location.public_id",
        read_only=True,
    )
    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
    )
    department_id = serializers.CharField(
        source="location.department.public_id",
        read_only=True,
    )
    department_name = serializers.CharField(
        source="location.department.name",
        read_only=True,
    )

    class Meta:
        model = Room
        fields = [
            "value",
            "label",
            "public_id",
            "name",
            "location_id",
            "location_name",
            "department_id",
            "department_name",
        ]