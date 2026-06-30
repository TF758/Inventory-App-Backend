from rest_framework import serializers
from access.services.roles import RoleGovernanceService
from access.hierachy import DEPARTMENT, LOCATION, ROOM, SITE
from access.services.hierachy import HierarchyService
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
    - Validate data shape and consistency.
    - Enforce role/scope compatibility.
    - Enforce exactly one scope where required.
    - Prevent duplicate assignments.

    Does NOT determine:
    - Permissions.
    - Object-level authorization.
    - Role governance.
    """

    user = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=User.objects.all(),
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
            "role",
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

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @staticmethod
    def _allowed_scope_levels(
        role,
    ):
        allowed = set()

        if HierarchyService.can_assign_to_site(
            role,
        ):
            allowed.add(
                SITE,
            )

        if HierarchyService.can_assign_to_department(
            role,
        ):
            allowed.add(
                DEPARTMENT,
            )

        if HierarchyService.can_assign_to_location(
            role,
        ):
            allowed.add(
                LOCATION,
            )

        if HierarchyService.can_assign_to_room(
            role,
        ):
            allowed.add(
                ROOM,
            )

        return allowed

    # -------------------------------------------------
    # Global validation
    # -------------------------------------------------

    def validate(
        self,
        attrs,
    ):
        role = attrs.get(
            "role",
            getattr(
                self.instance,
                "role",
                None,
            ),
        )

        if not role:
            raise serializers.ValidationError({
                "role": [
                    "Role must be provided."
                ]
            })

        target_user = attrs.get(
            "user",
            getattr(
                self.instance,
                "user",
                None,
            ),
        )

        if not target_user:
            raise serializers.ValidationError({
                "user": [
                    "User must be provided."
                ]
            })

        # Optional but recommended:
        # a role assignment should not be moved
        # from one user to another.
        if (
            self.instance
            and "user" in attrs
            and attrs["user"] != self.instance.user
        ):
            raise serializers.ValidationError({
                "user": [
                    "Role assignment user cannot be changed."
                ]
            })

        role_changed = (
            self.instance
            and role != self.instance.role
        )

        existing_room = None if role_changed else getattr(
            self.instance,
            "room",
            None,
        )

        existing_location = None if role_changed else getattr(
            self.instance,
            "location",
            None,
        )

        existing_department = None if role_changed else getattr(
            self.instance,
            "department",
            None,
        )

        room = attrs.get(
            "room",
            existing_room,
        )

        location = attrs.get(
            "location",
            existing_location,
        )

        department = attrs.get(
            "department",
            existing_department,
        )

        allowed_scope_levels = self._allowed_scope_levels(
            role,
        )

        if not allowed_scope_levels:
            raise serializers.ValidationError({
                "role": [
                    "Invalid role assignment configuration."
                ]
            })

        scope_values = {
            DEPARTMENT: department,
            LOCATION: location,
            ROOM: room,
        }

        provided_scope_levels = [
            level
            for level, value in scope_values.items()
            if value is not None
        ]

        # -------------------------------------------------
        # Site-level roles
        # -------------------------------------------------

        if SITE in allowed_scope_levels and len(
            allowed_scope_levels
        ) == 1:

            if provided_scope_levels:
                raise serializers.ValidationError({
                    "non_field_errors": [
                        f"{role} must not have a department, "
                        f"location, or room scope."
                    ]
                })

            department = None
            location = None
            room = None

        # -------------------------------------------------
        # Scoped roles
        # -------------------------------------------------

        else:

            if len(provided_scope_levels) != 1:
                raise serializers.ValidationError({
                    "non_field_errors": [
                        "Exactly one scope "
                        "(department, location, or room) "
                        "must be provided."
                    ]
                })

            selected_scope_level = provided_scope_levels[0]

            if selected_scope_level not in allowed_scope_levels:
                scope_name = {
                    DEPARTMENT: "department",
                    LOCATION: "location",
                    ROOM: "room",
                }[selected_scope_level]

                raise serializers.ValidationError({
                    scope_name: [
                        f"{role} cannot be assigned with "
                        f"{scope_name} scope."
                    ]
                })

        # -------------------------------------------------
        # Prevent duplicate assignments
        # -------------------------------------------------

        existing = RoleAssignment.objects.filter(
            user=target_user,
            role=role,
            department=department,
            location=location,
            room=room,
        )

        if self.instance:
            existing = existing.exclude(
                pk=self.instance.pk,
            )

        if existing.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    "User already has this role "
                    "in the specified scope."
                ]
            })

        attrs.update({
            "department": department,
            "location": location,
            "room": room,
        })

        return attrs

    # -------------------------------------------------
    # Create
    # -------------------------------------------------

    def create(
        self,
        validated_data,
    ):
        request = self.context.get(
            "request",
        )

        if (
            request
            and request.user.is_authenticated
        ):
            validated_data["assigned_by"] = request.user

        return super().create(
            validated_data,
        )

    # -------------------------------------------------
    # Update
    # -------------------------------------------------

    def update(
        self,
        instance,
        validated_data,
    ):
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