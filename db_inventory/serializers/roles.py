from rest_framework import serializers
from db_inventory.models.users import User
from db_inventory.models.site import Department, Location, Room
from db_inventory.models.roles import RoleAssignment
from db_inventory.permissions.helpers import ensure_permission
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied


class ActiveRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["active_role"]
        read_only_fields = ["active_role"]

    def validate_active_role(self, value):
        # Ensure the role assignment belongs to this user
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Cannot activate this role.")
        return value


class RoleReadSerializer(serializers.ModelSerializer):

    """Returns A user's Role and area (department/location/room)"""
    area_id = serializers.SerializerMethodField()
    area_type = serializers.SerializerMethodField()
    area_name = serializers.SerializerMethodField()
    assigned_by = serializers.CharField(source="assigned_by.username", read_only=True)
    user_public_id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    


    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "role",
            "user_public_id",
            "username",
            "public_id",
            "area_id",       # <-- generic id (public_id of dept/location/room)
            "area_type",     # <-- tells you which one it is
            "area_name",     # <-- display name
            "assigned_by",
            "assigned_date",
        ]

        read_only_fields = ["area_id", "area_type", "area_name", "public_id"]

    def get_area_id(self, obj):
        if obj.department:
            return obj.department.public_id
        if obj.location:
            return obj.location.public_id
        if obj.room:
            return obj.room.public_id
        return None

    def get_area_type(self, obj):
        if obj.department:
            return "department"
        if obj.location:
            return "location"
        if obj.room:
            return "room"
        return None

    def get_area_name(self, obj):
        if obj.department:
            return obj.department.name
        if obj.location:
            return obj.location.name
        if obj.room:
            return obj.room.name
        return "N/A"
    
    def get_user_public_id(self, obj):
        return obj.user.public_id if obj.user else None

    def get_username(self, obj):
        user = obj.user
        if not user:
            return "N/A"
        if user.fname and user.lname:
            return f"{user.fname} {user.lname}"
        return user.email or "N/A"

class RoleWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating RoleAssignment.

    Responsibilities:
    - Validate data shape & consistency
    - Enforce role ↔ scope compatibility
    - Enforce exactly one scope
    - Prevent duplicates
    - NO authority decisions (handled by permissions / viewset)
    """

    user = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=User.objects.all()
    )

    department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    location = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    class Meta:
        model = RoleAssignment
        fields = [
            "user",
            "role",
            "department",
            "location",
            "room",
            "assigned_by",
            "assigned_date",
        ]
        read_only_fields = ["assigned_by", "assigned_date"]

    # -------------------------------------------------
    # GLOBAL VALIDATION
    # -------------------------------------------------

    def validate(self, attrs):
        request = self.context.get("request")
        acting_user = request.user if request else None
        active_role = getattr(acting_user, "active_role", None)

        # -------- Resolve role --------
        role = attrs.get("role") or getattr(self.instance, "role", None)
        if not role:
            raise serializers.ValidationError("Role must be provided.")

        # -------- Resolve existing scope --------
        room = attrs.get("room", getattr(self.instance, "room", None))
        location = attrs.get("location", getattr(self.instance, "location", None))
        department = attrs.get("department", getattr(self.instance, "department", None))

        # =================================================
        # 🔑 NEW — Treat role change as full reassignment
        # =================================================
        if self.instance and role != self.instance.role:
            room = None
            location = None
            department = None

        # Re-apply incoming scope after reset
        room = attrs.get("room", room)
        location = attrs.get("location", location)
        department = attrs.get("department", department)

        # =================================================
        # ISSUE 2 — ROLE ↔ SCOPE COMPATIBILITY
        # =================================================
        ROLE_SCOPE_MAP = {
            "SITE": None,
            "DEPARTMENT": "department",
            "LOCATION": "location",
            "ROOM": "room",
        }

        prefix = role.split("_")[0]
        expected_scope = ROLE_SCOPE_MAP.get(prefix)

        if expected_scope is not None:
            for field, value in {
                "department": department,
                "location": location,
                "room": room,
            }.items():
                if field != expected_scope and value is not None:
                    raise serializers.ValidationError(
                        f"{role} cannot be assigned with {field} scope."
                    )

        # =================================================
        # ISSUE 3 — EXACTLY ONE SCOPE (or none for SITE)
        # =================================================
        scope_values = {
            "department": department,
            "location": location,
            "room": room,
        }

        non_null_scopes = [k for k, v in scope_values.items() if v is not None]

        if prefix == "SITE":
            if non_null_scopes:
                raise serializers.ValidationError(
                    "SITE_ADMIN role must not have a scope."
                )
        else:
            if len(non_null_scopes) != 1:
                raise serializers.ValidationError(
                    "Exactly one scope (department, location, or room) must be provided."
                )

        # =================================================
        # Prevent duplicate role assignments
        # =================================================
        target_user = attrs.get("user") or getattr(self.instance, "user", None)

        existing = RoleAssignment.objects.filter(
            user=target_user,
            role=role,
            department=department,
            location=location,
            room=room,
        )

        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError(
                "User already has this role in the specified scope."
            )

        # Final normalized attrs
        attrs.update({
            "department": department,
            "location": location,
            "room": room,
        })

        return attrs

    # -------------------------------------------------
    # CREATE / UPDATE
    # -------------------------------------------------

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["assigned_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # ISSUE 4 — Do NOT overwrite assigned_by on update
        validated_data.pop("assigned_by", None)
        return super().update(instance, validated_data)


__all__ = [
    "RoleReadSerializer",
    "RoleWriteSerializer",
    "ActiveRoleSerializer",
]