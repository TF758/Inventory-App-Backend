from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from core.services.security.login_failures import is_temporarily_locked
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
                "Access token missing session_id.",
                code="invalid_token",
            )

        # -----------------------------------------
        # Absolute expiry (token-level, immutable)
        # -----------------------------------------

        abs_exp = validated_token.get("abs_exp")

        now_ts = int(time.time())

        if not abs_exp or abs_exp <= now_ts:

            raise AuthenticationFailed(
                "Session has expired.",
                code="expired_session",
            )

        # -----------------------------------------
        # Resolve session
        # -----------------------------------------

        try:

            session = UserSession.objects.get(
                id=session_id
            )

        except UserSession.DoesNotExist:

            raise AuthenticationFailed(
                "Session does not exist or has been revoked.",
                code="invalid_session",
            )

        # -----------------------------------------
        # Status validation
        # -----------------------------------------

        if session.status != UserSession.Status.ACTIVE:

            raise AuthenticationFailed(
                "Session revoked or expired.",
                code="invalid_session",
            )

        # -----------------------------------------
        # Idle expiry
        # -----------------------------------------

        if session.expires_at <= timezone.now():

            session.status = (
                UserSession.Status.EXPIRED
            )

            session.save(update_fields=["status"])

            raise AuthenticationFailed(
                "Session has expired.",
                code="expired_session",
            )

        # -----------------------------------------
        # Account lock enforcement
        # -----------------------------------------

        if user.is_locked:

            session.status = (
                UserSession.Status.REVOKED
            )

            session.save(update_fields=["status"])

            raise AuthenticationFailed(
                "Account locked.",
                code="account_locked",
            )

        if is_temporarily_locked(user):

            raise AuthenticationFailed(
                "Account temporarily locked.",
                code="account_temporarily_locked",
            )

        # -----------------------------------------
        # Expose session downstream
        # -----------------------------------------

        self.session = session

        return user