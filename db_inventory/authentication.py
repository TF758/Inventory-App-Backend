# db_inventory/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from .models import UserSession

class SessionJWTAuthentication(JWTAuthentication):
    """
    Extends JWTAuthentication to enforce session-based revocation.
    Checks that the session tied to the access token is active.
    """

    def get_user(self, validated_token):
        """
        Overrides JWTAuthentication.get_user to include session validation.
        """
        # First, resolve the user as usual
        user = super().get_user(validated_token)

        # Access the session_id claim from the token
        session_id = validated_token.get("session_id")
        if not session_id:
            raise AuthenticationFailed(
                "Access token missing session_id.", code="invalid_token"
            )

        try:
            session = UserSession.objects.get(id=session_id)
        except UserSession.DoesNotExist:
            raise AuthenticationFailed(
                "Session does not exist or has been revoked.", code="invalid_session"
            )

        if session.status != UserSession.Status.ACTIVE:
            raise AuthenticationFailed(
                "Session revoked or expired.", code="invalid_session"
            )

        # Optional: attach session to request for downstream use
        setattr(self, "session", session)

        return user
