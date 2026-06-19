from sites.models.sites import Department, Location, Room
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers



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

        return attrs