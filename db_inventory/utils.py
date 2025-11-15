from django.core import signing
from datetime import timedelta
from django.utils import timezone

class ExcludeFiltersMixin:
    """
    Allows excluding filter fields from a filterset dynamically.
    Ensures excluded fields are removed both at runtime and from schema generation.
    """
    exclude_filter_fields: list[str] = []

    def get_filterset_class(self):
        base_class = super().get_filterset_class()
        exclude = set(self.exclude_filter_fields)

        # Dynamically subclass the base filterset
        class DynamicFilterset(base_class):
            class Meta(base_class.Meta):
                fields = {
                    k: v for k, v in base_class.Meta.fields.items()
                    if k not in exclude
                }

        return DynamicFilterset


def get_serializer_field_info(serializer_class):
    """
    Return a dict of field metadata for a given serializer.
    Example output:
    {
        "name": {"required": True, "allow_null": False, "max_length": 100},
        "brand": {"required": False, "allow_null": True, "max_length": 100},
        ...
    }
    """
    serializer = serializer_class()
    field_info = {}

    for field_name, field in serializer.fields.items():
        info = {
            "required": field.required,
            "allow_null": getattr(field, "allow_null", False),
            "allow_blank": getattr(field, "allow_blank", False),
        }
        if hasattr(field, "max_length") and field.max_length:
            info["max_length"] = field.max_length
        if hasattr(field, "min_length") and field.min_length:
            info["min_length"] = field.min_length
        if hasattr(field, "choices") and field.choices:
            info["choices"] = list(field.choices.keys())
        field_info[field_name] = info

    return field_info


class PasswordResetToken:
    SALT = 'password_reset_salt'
    EXPIRATION_MINUTES = 10

    @classmethod
    def generate_token(cls, user_public_id):
        data = {
            'user_id': user_public_id,
            'timestamp': timezone.now().timestamp(),
        }
        return signing.dumps(data, salt=cls.SALT)

    @classmethod
    def validate_token(cls, token):
        try:
            data = signing.loads(token, salt=cls.SALT, max_age=cls.EXPIRATION_MINUTES * 60)
            return data['user_id']
        except signing.BadSignature:
            return None
        except signing.SignatureExpired:
            return None

def user_can_access_role(user, role_obj):
    """
    Checks if the user's active_role allows read access to the given RoleAssignment.
    """
    active = getattr(user, "active_role", None)
    if not active:
        return False

    if isinstance(active, dict):
        active_role_name = active.get("role")
        active_dep = active.get("department")
        active_loc = active.get("location")
        active_room = active.get("room")
    else:
        active_role_name = getattr(active, "role", None)
        active_dep = getattr(active, "department", None)
        active_loc = getattr(active, "location", None)
        active_room = getattr(active, "room", None)

    if user.is_superuser or active_role_name == "SITE_ADMIN":
        return True

    # Read-only scoping for department
    if active_role_name == "DEPARTMENT_ADMIN":
        return (
            role_obj.department == active_dep
            or (role_obj.location and role_obj.location.department == active_dep)
            or (role_obj.room and role_obj.room.location.department == active_dep)
        )

    # Location scoping
    if active_role_name == "LOCATION_ADMIN":
        role_location = role_obj.location or getattr(role_obj.room, "location", None)
        return role_location == active_loc

    # Room scoping
    if active_role_name == "ROOM_ADMIN":
        return role_obj.room == active_room

    # Viewer/clerk roles can only see their room
    if active_role_name in ["ROOM_VIEWER", "ROOM_CLERK"]:
        return role_obj.room == active_room

    return False
