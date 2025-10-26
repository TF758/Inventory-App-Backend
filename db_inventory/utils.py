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