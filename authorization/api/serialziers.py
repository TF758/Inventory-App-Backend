from rest_framework import serializers
from authorization.models import  Permission, Role, RolePermission


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
    permissions = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
    )

    def validate_permissions(self, value):
        existing_codes = set(
            Permission.objects.filter(
                code__in=value
            ).values_list(
                "code",
                flat=True,
            )
        )

        missing = sorted(
            set(value) - existing_codes
        )

        if missing:
            raise serializers.ValidationError(
                f"Unknown permissions: {', '.join(missing)}"
            )

        return value