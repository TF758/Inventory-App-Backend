from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from .models import UserSession
from django.utils import timezone
import time


class SessionJWTAuthentication(JWTAuthentication):
    """
    Enforces session-based access control on top of JWT authentication.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        session_id = validated_token.get("session_id")
        if not session_id:
            raise AuthenticationFailed(
                "Access token missing session_id.", code="invalid_token"
            )

        # --- Absolute expiry (token-level, immutable) ---
        abs_exp = validated_token.get("abs_exp")
        now_ts = int(time.time())

        if not abs_exp or abs_exp <= now_ts:
            raise AuthenticationFailed(
                "Session has expired.", code="expired_session"
            )

        try:
            session = UserSession.objects.get(id=session_id)
        except UserSession.DoesNotExist:
            raise AuthenticationFailed(
                "Session does not exist or has been revoked.",
                code="invalid_session",
            )

        # --- Status check first ---
        if session.status != UserSession.Status.ACTIVE:
            raise AuthenticationFailed(
                "Session revoked or expired.", code="invalid_session"
            )

        # --- Idle expiry ---
        if session.expires_at <= timezone.now():
            raise AuthenticationFailed(
                "Session has expired.", code="expired_session"
            )

        # Optional: expose session downstream
        self.session = session

        return user
