from rest_framework import serializers

from authorization.models import ( Permission, Role, RolePermission, )


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = (
            "id",
            "public_id",
            "code",
            "name",
            "description",
            "module",
            "is_system",
        )
        read_only_fields = fields


class RolePermissionSerializer(serializers.ModelSerializer):
    permission = PermissionSerializer(read_only=True)

    class Meta:
        model = RolePermission
        fields = (
            "id",
            "permission",
            "enabled",
            "updated_at",
        )
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "public_id",
            "code",
            "name",
            "scope_type",
            "level",
            "is_system_role",
            "permission_count",
        )
        read_only_fields = fields

    def get_permission_count(self, obj):
        return obj.role_permissions.filter(
            enabled=True
        ).count()


class RoleDetailSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "public_id",
            "code",
            "name",
            "scope_type",
            "level",
            "is_system_role",
            "permission_count",
            "permissions",
        )
        read_only_fields = fields

    def get_permission_count(self, obj):
        return obj.role_permissions.filter(
            enabled=True
        ).count()

    def get_permissions(self, obj):
        permissions = [
            rp.permission
            for rp in obj.role_permissions.all()
            if rp.enabled
        ]

        return PermissionSerializer(
            permissions,
            many=True,
            context=self.context,
        ).data


class RolePermissionUpdateSerializer(serializers.Serializer):
    """
    Used by the permission matrix UI.

    Payload:

    {
        "permissions": [
            "assets.view",
            "assets.create",
            "assets.update"
        ]
    }

    The target role is supplied by the endpoint URL.
    """

    permissions = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
    )

    def validate_permissions(self, permissions):

        # Prevent duplicate entries
        duplicates = {
            code
            for code in permissions
            if permissions.count(code) > 1
        }

        if duplicates:
            raise serializers.ValidationError(
                (
                    "Duplicate permissions: "
                    f"{', '.join(sorted(duplicates))}"
                )
            )

        existing_codes = set(
            Permission.objects.filter(
                code__in=permissions,
            ).values_list(
                "code",
                flat=True,
            )
        )

        missing = sorted(
            set(permissions)
            - existing_codes
        )

        if missing:
            raise serializers.ValidationError(
                (
                    "Unknown permissions: "
                    f"{', '.join(missing)}"
                )
            )

        return permissions


class PermissionMatrixUpdateSerializer(
    serializers.Serializer
):
    """
    Payload:

    {
        "assignments": {
            "<role_public_id>": [
                "assets.view",
                "assets.create"
            ]
        }
    }
    """

    assignments = serializers.DictField(
        child=serializers.ListField(
            child=serializers.CharField(),
            allow_empty=True,
        )
    )

    def validate_assignments(self, assignments):

        role_public_ids = set(
            Role.objects.filter(
                public_id__in=assignments.keys()
            ).values_list(
                "public_id",
                flat=True,
            )
        )

        missing_roles = sorted(
            str(role_id)
            for role_id in (
                set(assignments.keys())
                - {str(x) for x in role_public_ids}
            )
        )

        if missing_roles:
            raise serializers.ValidationError(
                (
                    "Unknown roles: "
                    f"{', '.join(missing_roles)}"
                )
            )

        all_codes = set()

        for permission_codes in assignments.values():

            duplicates = {
                code
                for code in permission_codes
                if permission_codes.count(code) > 1
            }

            if duplicates:
                raise serializers.ValidationError(
                    (
                        "Duplicate permissions: "
                        f"{', '.join(sorted(duplicates))}"
                    )
                )

            all_codes.update(
                permission_codes
            )

        existing_codes = set(
            Permission.objects.filter(
                code__in=all_codes
            ).values_list(
                "code",
                flat=True,
            )
        )

        missing_permissions = sorted(
            all_codes - existing_codes
        )

        if missing_permissions:
            raise serializers.ValidationError(
                (
                    "Unknown permissions: "
                    f"{', '.join(missing_permissions)}"
                )
            )

        return assignments