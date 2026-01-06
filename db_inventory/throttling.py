from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.exceptions import Throttled

class LoginThrottle(AnonRateThrottle):
    scope = "login"

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