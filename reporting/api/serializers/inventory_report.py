from sites.models.sites import Department, Location, Room
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers


def enforce_inventory_summary_scope(user, validated_data):
    """
    Prevent users from requesting reports above their authorized scope.

    Expected validated_data:
    {
        "scope": "global|department|location|room",
        "scope_id": "PUBLIC_ID|None"
    }

    Uses user's active_role (RoleAssignment).
    """

    scope = validated_data["scope"]
    scope_id = validated_data.get("scope_id")

    role = getattr(user, "active_role", None)

    if not role:
        raise PermissionDenied(
            "You do not have an active administrative role."
        )

    actor_role = role.role

    # -------------------------------------------------
    # SITE ADMIN
    # Full access to all scopes
    # -------------------------------------------------
    if actor_role == "SITE_ADMIN":
        return

    # -------------------------------------------------
    # DEPARTMENT ROLES
    # Can access:
    # - own department
    # - locations inside own department
    # - rooms inside own department
    # Cannot access global
    # -------------------------------------------------
    if actor_role.startswith("DEPARTMENT"):

        if scope == "global":
            raise PermissionDenied(
                "You cannot request global reports."
            )

        if scope == "department":
            if str(role.department.public_id).lower() != scope_id.lower():
                raise PermissionDenied(
                    "You can only access your assigned department."
                )
            return

        if scope == "location":
            allowed = Location.objects.filter(
                public_id__iexact=scope_id,
                department=role.department,
            ).exists()

            if not allowed:
                raise PermissionDenied(
                    "That location is outside your department."
                )
            return

        if scope == "room":
            allowed = Room.objects.filter(
                public_id__iexact=scope_id,
                location__department=role.department,
            ).exists()

            if not allowed:
                raise PermissionDenied(
                    "That room is outside your department."
                )
            return

    # -------------------------------------------------
    # LOCATION ROLES
    # Can access:
    # - own location
    # - rooms inside own location
    # Cannot access department/global
    # -------------------------------------------------
    if actor_role.startswith("LOCATION"):

        if scope in {"global", "department"}:
            raise PermissionDenied(
                "You cannot request reports above location scope."
            )

        if scope == "location":
            if str(role.location.public_id).lower() != scope_id.lower():
                raise PermissionDenied(
                    "You can only access your assigned location."
                )
            return

        if scope == "room":
            allowed = Room.objects.filter(
                public_id__iexact=scope_id,
                location=role.location,
            ).exists()

            if not allowed:
                raise PermissionDenied(
                    "That room is outside your location."
                )
            return

    # -------------------------------------------------
    # ROOM ROLES
    # Can access own room only
    # -------------------------------------------------
    if actor_role.startswith("ROOM"):

        if scope != "room":
            raise PermissionDenied(
                "You may only request room-level reports."
            )

        if str(role.room.public_id).lower() != scope_id.lower():
            raise PermissionDenied(
                "You may only access your assigned room."
            )

        return

    # -------------------------------------------------
    # Unknown / unsupported role
    # -------------------------------------------------
    raise PermissionDenied(
        "Your role is not authorized for this report."
    )


class InventorySummaryReportRequestSerializer(serializers.Serializer):
    """
    Request payload:

    {
        "scope": "global|department|location|room",
        "scope_id": "PUBLIC_ID"   # required unless global
    }
    """

    SCOPE_CHOICES = [
        ("global", "Global"),
        ("department", "Department"),
        ("location", "Location"),
        ("room", "Room"),
    ]

    scope = serializers.ChoiceField(
        choices=SCOPE_CHOICES,
        help_text="Scope level for the report."
    )

    scope_id = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="Public ID for Department / Location / Room."
    )

    def validate_scope_id(self, value):
        return value.strip()

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        scope = attrs.get("scope")
        scope_id = attrs.get("scope_id")

        # -----------------------------------------
        # Global scope requires no identifier
        # -----------------------------------------
        if scope == "global":
            attrs["scope_id"] = None

        else:
            # -----------------------------------------
            # Non-global scopes require scope_id
            # -----------------------------------------
            if not scope_id:
                raise serializers.ValidationError({
                    "scope_id": (
                        "This field is required "
                        "for non-global scopes."
                    )
                })

            model_map = {
                "department": Department,
                "location": Location,
                "room": Room,
            }

            model = model_map[scope]

            exists = model.objects.filter(
                public_id__iexact=scope_id
            ).exists()

            if not exists:
                raise serializers.ValidationError({
                    "scope_id": (
                        f"Invalid {scope} identifier."
                    )
                })

            attrs["scope_id"] = scope_id.strip()

        # -----------------------------------------
        # Scope authorization enforcement
        # -----------------------------------------
        if user and user.is_authenticated:
            enforce_inventory_summary_scope(user, attrs)

        return attrs