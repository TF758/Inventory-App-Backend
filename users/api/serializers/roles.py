from rest_framework import serializers
from inventory.authorization.models import Role
from users.models.roles import RoleAssignment
from users.models.users import User
from sites.models.sites import Department, Location, Room

from rest_framework import serializers


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

    Does NOT:
    - Make authorization decisions
    - Enforce delegation rules
    - Enforce scope authority

    Those belong in permission classes and services.
    """

    user = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=User.objects.all(),
    )

    role_ref = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Role.objects.all(),
    )

    department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    location = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = RoleAssignment

        fields = [
            "user",
            "role_ref",
            "department",
            "location",
            "room",
            "assigned_by",
            "assigned_date",
        ]

        read_only_fields = [
            "assigned_by",
            "assigned_date",
        ]

        validators = []

    def validate(self, attrs):

        role_ref = (
            attrs.get("role_ref")
            or getattr(self.instance, "role_ref", None)
        )

        if not role_ref:
            raise serializers.ValidationError(
                "Role must be provided."
            )

        # -----------------------------------------
        # Resolve scope
        # -----------------------------------------

        room = attrs.get(
            "room",
            getattr(self.instance, "room", None),
        )

        location = attrs.get(
            "location",
            getattr(self.instance, "location", None),
        )

        department = attrs.get(
            "department",
            getattr(self.instance, "department", None),
        )

        # -----------------------------------------
        # Treat role change as reassignment
        # -----------------------------------------

        if (
            self.instance
            and role_ref != self.instance.role_ref
        ):
            room = None
            location = None
            department = None

        room = attrs.get("room", room)
        location = attrs.get("location", location)
        department = attrs.get("department", department)

        # -----------------------------------------
        # Scope compatibility
        # -----------------------------------------

        scope_field_map = {
            "ROOM": "room",
            "LOCATION": "location",
            "DEPARTMENT": "department",
            "GLOBAL": None,
        }

        expected_scope = scope_field_map.get(
            role_ref.scope_type
        )

        if expected_scope is not None:

            for field, value in {
                "department": department,
                "location": location,
                "room": room,
            }.items():

                if (
                    field != expected_scope
                    and value is not None
                ):
                    raise serializers.ValidationError(
                        f"{role_ref.name} cannot be assigned with {field} scope."
                    )

        # -----------------------------------------
        # Exactly one scope
        # -----------------------------------------

        scope_values = {
            "department": department,
            "location": location,
            "room": room,
        }

        non_null_scopes = [
            key
            for key, value in scope_values.items()
            if value is not None
        ]

        if role_ref.scope_type == "GLOBAL":

            if non_null_scopes:
                raise serializers.ValidationError(
                    "Global roles cannot have scope."
                )

        else:

            if len(non_null_scopes) != 1:
                raise serializers.ValidationError(
                    "Exactly one scope (department, location, or room) must be provided."
                )

        # -----------------------------------------
        # Prevent duplicate assignments
        # -----------------------------------------

        target_user = (
            attrs.get("user")
            or getattr(self.instance, "user", None)
        )

        existing = RoleAssignment.objects.filter(
            user=target_user,
            role_ref=role_ref,
            department=department,
            location=location,
            room=room,
        )

        if self.instance:
            existing = existing.exclude(
                pk=self.instance.pk
            )

        if existing.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    "User already has this role in the specified scope."
                ]
            })

        attrs.update({
            "department": department,
            "location": location,
            "room": room,
        })

        return attrs

    def create(self, validated_data):

        request = self.context.get("request")

        if (
            request
            and request.user.is_authenticated
        ):
            validated_data["assigned_by"] = request.user

        return super().create(validated_data)

    def update( self, instance, validated_data, ):
        validated_data.pop(
            "assigned_by",
            None,
        )

        return super().update(
            instance,
            validated_data,
        )


__all__ = [
    "RoleReadSerializer",
    "RoleWriteSerializer",
    "ActiveRoleSerializer",
]