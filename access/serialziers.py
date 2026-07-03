from rest_framework import serializers

from access.models import Permission
from access.role_permission_boundaries import (
    is_permission_allowed_for_role,
)
from users.models.roles import RoleAssignment


CONFIGURABLE_ROLE_CHOICES = [
    (role, label)
    for role, label in RoleAssignment.ROLE_CHOICES
    if role != "SITE_ADMIN"
]


class RolePermissionToggleSerializer(
    serializers.Serializer,
):
    role = serializers.ChoiceField(
        choices=CONFIGURABLE_ROLE_CHOICES,
    )

    enabled = serializers.BooleanField()


class PermissionMatrixPermissionSerializer(
    serializers.Serializer,
):
    code = serializers.CharField()

    roles = RolePermissionToggleSerializer(
        many=True,
    )

    def validate_code(self, value):
        code = value.strip()

        if not Permission.objects.filter(
            code=code,
            is_configurable=True,
        ).exists():
            raise serializers.ValidationError(
                "Unknown or non-configurable permission."
            )

        return code

    def validate_roles(self, value):
        roles = [
            item["role"]
            for item in value
        ]

        duplicates = {
            role
            for role in roles
            if roles.count(role) > 1
        }

        if duplicates:
            raise serializers.ValidationError(
                "Duplicate role toggles are not allowed: "
                + ", ".join(
                    sorted(duplicates)
                )
            )

        return value

    def validate(self, attrs):
        permission_code = attrs.get(
            "code",
            "",
        )

        roles = attrs.get(
            "roles",
            [],
        )

        invalid_roles = [
            item["role"]
            for item in roles
            if item.get("enabled") is True
            and not is_permission_allowed_for_role(
                item["role"],
                permission_code,
            )
        ]

        if invalid_roles:
            if len(invalid_roles) == 1:
                raise serializers.ValidationError({
                    "roles": [
                        f"{invalid_roles[0]} cannot be granted "
                        f"{permission_code}."
                    ]
                })

            raise serializers.ValidationError({
                "roles": [
                    "These roles cannot be granted "
                    f"{permission_code}: "
                    + ", ".join(
                        sorted(invalid_roles)
                    )
                ]
            })

        return attrs


class PermissionMatrixDomainSerializer(
    serializers.Serializer,
):
    code = serializers.CharField()

    permissions = (
        PermissionMatrixPermissionSerializer(
            many=True,
        )
    )

    def validate_permissions(self, value):
        codes = [
            item["code"]
            for item in value
        ]

        duplicates = {
            code
            for code in codes
            if codes.count(code) > 1
        }

        if duplicates:
            raise serializers.ValidationError(
                "Duplicate permissions are not allowed: "
                + ", ".join(
                    sorted(duplicates)
                )
            )

        return value


class PermissionMatrixUpdateSerializer(
    serializers.Serializer,
):
    domains = (
        PermissionMatrixDomainSerializer(
            many=True,
        )
    )

    def validate_domains(self, value):
        domain_codes = [
            item["code"]
            for item in value
        ]

        duplicates = {
            code
            for code in domain_codes
            if domain_codes.count(code) > 1
        }

        if duplicates:
            raise serializers.ValidationError(
                "Duplicate domains are not allowed: "
                + ", ".join(
                    sorted(duplicates)
                )
            )

        return value