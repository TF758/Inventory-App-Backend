from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.exceptions import Throttled
from django.conf import settings

class LoginThrottle(AnonRateThrottle):
    scope = "login"

    def allow_request(self, request, view):
        # Disable throttling during tests
        if getattr(settings, "IS_TESTING", False):
            return True
        return super().allow_request(request, view)

    def throttle_failure(self):
        raise Throttled(
            detail={
                "error": "Too many login attempts. Try again later",
            }
        )


class RefreshTokenThrottle(AnonRateThrottle):
    scope = "token_refresh"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "password_reset"

    def throttle_failure(self):
        raise Throttled(
            detail={
                "error": "Too many password attempts. Try again later",
            }
        )


# --- GENERAL API ---
class UserReadThrottle(UserRateThrottle):
    scope = "user_read"


class EquipmentActionThrottle(UserRateThrottle):
    scope = "equipment_action"


class AdminActionThrottle(UserRateThrottle):
    scope = "admin_action"