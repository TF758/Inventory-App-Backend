import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.logging import get_logger
from core.mixins import AuditMixin
from core.models.audit import AuditLog
from core.models.sessions import UserSession
from core.security_policy import *
from core.serializers.auth import PasswordResetConfirmSerializer
from core.serializers.general import (
    PasswordResetRequestSerializer,
    SessionTokenLoginViewSerializer,
)
from core.services.security.login_failures import (
    is_temporarily_locked,
    register_failed_login,
    reset_failed_logins,
    validate_user_not_locked,
)
from core.throttling import LoginThrottle, RefreshTokenThrottle
from core.utils.tokens import PasswordResetToken
from users.models import User


logger = get_logger(__name__)

SESSION_ID_HEADER = "X-Session-ID"
REFRESH_COOKIE_PREFIX = "refresh_"
LEGACY_REFRESH_COOKIE_NAME = "refresh"


def refresh_cookie_name(session_id: uuid.UUID | str) -> str:
    """Return the HttpOnly refresh-cookie name for one selected session."""
    return f"{REFRESH_COOKIE_PREFIX}{session_id}"


def parse_session_id(request) -> uuid.UUID | None:
    """Read and strictly validate the non-secret session selector header."""
    raw_session_id = request.headers.get(SESSION_ID_HEADER)

    if not raw_session_id:
        return None

    try:
        return uuid.UUID(str(raw_session_id).strip())
    except (TypeError, ValueError, AttributeError):
        return None


class SessionTokenLoginView(TokenObtainPairView):

    serializer_class = SessionTokenLoginViewSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        ip = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]

        email = request.data.get("email")

        # -----------------------------------------
        # Load security policy
        # -----------------------------------------

        policy = SecuritySettings.load()

        # -----------------------------------------
        # Resolve user (if exists)
        # -----------------------------------------

        user = User.objects.filter(
            email__iexact=email
        ).first()

        # -----------------------------------------
        # Pre-auth lock validation
        # -----------------------------------------

        try:

            if user:
                validate_user_not_locked(user)

        except AuthenticationFailed as exc:

            AuditLog.objects.create(
                event_type=AuditLog.Events.ACCOUNT_LOCKED,
                user=user,
                user_public_id=str(user.public_id),
                user_email=user.email,
                description="Login attempt on locked account",
                metadata={
                    "reason": str(exc),
                    "attempted_login": True,
                    "lock_type": (
                        "temporary"
                        if is_temporarily_locked(user)
                        else "permanent"
                    ),
                },
                ip_address=ip,
                user_agent=user_agent,
            )

            raise

        # -----------------------------------------
        # Authenticate user
        # -----------------------------------------

        try:

            serializer.is_valid(raise_exception=True)

        except Exception as exc:

            lock_result = None

            # -----------------------------------------
            # Register failed login attempt
            # -----------------------------------------

            if user:

                lock_result = register_failed_login(
                    user=user,
                    policy=policy,
                )

            # -----------------------------------------
            # Failed login audit
            # -----------------------------------------

            AuditLog.objects.create(
                event_type=AuditLog.Events.LOGIN_FAILED,
                user=user,
                user_public_id=(
                    str(user.public_id)
                    if user else ""
                ),
                user_email=(
                    user.email
                    if user else email
                ),
                description="Invalid login credentials",
                metadata={
                    "reason": str(exc),
                },
                ip_address=ip,
                user_agent=user_agent,
            )

            # -----------------------------------------
            # Account lock audit
            # -----------------------------------------

            if (
                lock_result
                and (
                    lock_result["temporarily_locked"]
                    or lock_result["permanently_locked"]
                )
            ):

                AuditLog.objects.create(
                    event_type=AuditLog.Events.ACCOUNT_LOCKED,
                    user=user,
                    user_public_id=str(user.public_id),
                    user_email=user.email,
                    description="Account locked after failed login attempts",
                    metadata={
                        "lock_type": (
                            "permanent"
                            if lock_result["permanently_locked"]
                            else "temporary"
                        ),
                        "failed_attempts":
                        lock_result["failed_attempts"],
                    },
                    ip_address=ip,
                    user_agent=user_agent,
                )

            raise

        user = serializer.user
        now = timezone.now()

        # -----------------------------------------
        # Reset failed login tracking
        # -----------------------------------------

        reset_failed_logins(user)

        # -----------------------------------------
        # Generate refresh token
        # -----------------------------------------

        raw_refresh = secrets.token_urlsafe(64)

        try:

            hashed_refresh = UserSession.hash_token(
                raw_refresh
            )

        except Exception:

            logger.exception(
                "refresh_token_hashing_failed",
                extra={
                    "user_id": user.pk,
                    "has_user_agent": bool(user_agent),
                },
            )

            raise APIException(
                "Authentication failed."
            )

        # -----------------------------------------
        # Create session
        # -----------------------------------------

        try:

            with transaction.atomic():

                ua_hash = UserSession.hash_user_agent(
                    user_agent
                )

                device_name = request.headers.get(
                    "X-Device-Name"
                )

                active_sessions = UserSession.objects.filter(
                    user=user,
                    status=UserSession.Status.ACTIVE,
                ).order_by("created_at")

                # -----------------------------------------
                # Enforce concurrent session policy
                # -----------------------------------------

                if (
                    active_sessions.count()
                    >= policy.max_concurrent_sessions
                ):

                    oldest_session = active_sessions.first()

                    if oldest_session:

                        oldest_session.status = (
                            UserSession.Status.REVOKED
                        )

                        oldest_session.save(
                            update_fields=["status"]
                        )

                        AuditLog.objects.create(
                            event_type=(
                                AuditLog.Events
                                .SESSION_REVOKED
                            ),
                            user=user,
                            user_public_id=str(
                                user.public_id
                            ),
                            user_email=user.email,
                            description=(
                                "Session revoked due to "
                                "maximum concurrent sessions"
                            ),
                            metadata={
                                "reason":
                                "max_concurrent_sessions",
                            },
                        )

                session = UserSession.objects.create(
                    user=user,
                    refresh_token_hash=hashed_refresh,
                    device_name=device_name,
                    last_ip_address=ip,
                    expires_at=(
                        now +
                        get_session_idle_timeout()
                    ),
                    absolute_expires_at=(
                        now +
                        get_session_absolute_lifetime()
                    ),
                    user_agent_hash=ua_hash,
                    ip_address=ip,
                )

        except Exception:

            logger.exception(
                "session_creation_failed",
                extra={
                    "user_id": user.pk,
                    "max_sessions":
                    policy.max_concurrent_sessions,
                },
            )

            raise APIException(
                "Authentication failed."
            )

        # -----------------------------------------
        # Generate access token
        # -----------------------------------------

        try:

            access_token_obj = AccessToken.for_user(user)

            access_token_obj.set_exp(
                lifetime=get_access_token_lifetime()
            )

            access_token_obj["session_id"] = str(
                session.id
            )

            access_token_obj["abs_exp"] = int(
                session.absolute_expires_at.timestamp()
            )

            access_token_obj["idle_exp"] = int(
                session.expires_at.timestamp()
            )

            access_token = str(access_token_obj)

        except Exception:

            logger.exception(
                "access_token_generation_failed",
                extra={
                    "user_id": user.pk,
                    "session_id": session.id,
                },
            )

            session.delete()

            raise APIException(
                "Authentication failed."
            )

        # -----------------------------------------
        # Update last login
        # -----------------------------------------

        user.last_login = now

        user.save(update_fields=["last_login"])

        # -----------------------------------------
        # Successful login audit
        # -----------------------------------------

        AuditLog.objects.create(
            event_type=AuditLog.Events.LOGIN,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
            ip_address=ip,
            user_agent=user_agent,
        )

        # -----------------------------------------
        # Response
        # -----------------------------------------

        response_data = {
            "access": access_token,
            "session_id": str(session.id),
            "public_id": str(user.public_id),
            "role_id": (
                user.active_role.public_id
                if user.active_role
                else None
            ),
            "force_password_change":
            user.force_password_change,
        }

        response = Response(
            response_data,
            status=status.HTTP_200_OK,
        )

        cookie_name = refresh_cookie_name(session.id)

        response.set_cookie(
            key=cookie_name,
            value=raw_refresh,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            path="/",
            max_age=int(
                get_session_absolute_lifetime()
                .total_seconds()
            ),
        )

        # Remove the former shared cookie during the migration to
        # session-specific refresh credentials.
        response.delete_cookie(LEGACY_REFRESH_COOKIE_NAME, path="/")

        return response
    


class RefreshAPIView(APIView):
    """
    Rotate one selected session's refresh token and return a new access token.

    The frontend supplies the non-secret session selector in X-Session-ID.
    The raw refresh credential remains in the matching session-specific
    HttpOnly cookie, refresh_<session_id>. The selector alone never
    authenticates the request.

    Refreshes for the same session are serialized with select_for_update().
    An immediately previous token from the same user agent and inside the
    configured grace period returns HTTP 409 so a sibling tab can retry using
    the cookie installed by the winning refresh response.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [RefreshTokenThrottle]

    @staticmethod
    def _client_ip(request) -> str | None:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _invalid_session_response(
        *,
        cookie_name: str | None = None,
        code: str = "INVALID_SESSION",
        detail: str = "Invalid or expired session.",
    ) -> Response:
        response = Response(
            {
                "code": code,
                "detail": detail,
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

        if cookie_name:
            response.delete_cookie(cookie_name, path="/")

        return response

    @staticmethod
    def _refresh_conflict_response(session_id: uuid.UUID) -> Response:
        response = Response(
            {
                "code": "REFRESH_CONFLICT",
                "detail": (
                    "Another browser tab refreshed this session. "
                    "Retry the refresh request."
                ),
                "session_id": str(session_id),
            },
            status=status.HTTP_409_CONFLICT,
        )
        response["Retry-After"] = "1"
        return response

    @staticmethod
    def _revoke_family(session: UserSession, *, reason: str) -> None:
        UserSession.objects.filter(
            session_family=session.session_family,
        ).update(status=UserSession.Status.REVOKED)

        AuditLog.objects.create(
            event_type=AuditLog.Events.SESSION_REVOKED,
            user=session.user,
            user_public_id=str(session.user.public_id),
            user_email=session.user.email,
            metadata={
                "reason": reason,
                "family": str(session.session_family),
                "session_id": str(session.id),
            },
        )

    def post(self, request):
        session_id = parse_session_id(request)

        if session_id is None:
            return self._invalid_session_response(
                code="INVALID_SESSION_ID",
                detail=(
                    f"A valid {SESSION_ID_HEADER} header is required."
                ),
            )

        cookie_name = refresh_cookie_name(session_id)
        raw_refresh = request.COOKIES.get(cookie_name)

        if not raw_refresh:
            return self._invalid_session_response(cookie_name=cookie_name)

        try:
            hashed_refresh = UserSession.hash_token(raw_refresh)
        except Exception:
            logger.exception(
                "refresh_token_hashing_failed",
                extra={
                    "session_id": str(session_id),
                    "has_refresh_cookie": True,
                },
            )
            return Response(
                {
                    "code": "REFRESH_INTERNAL_ERROR",
                    "detail": "Internal server error.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        now = timezone.now()
        ip_address = self._client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]
        request_user_agent_hash = UserSession.hash_user_agent(user_agent)

        grace_seconds = int(
            getattr(settings, "REFRESH_REUSE_GRACE_SECONDS", 5)
        )
        grace_period = timedelta(seconds=max(grace_seconds, 0))

        try:
            new_raw_refresh = secrets.token_urlsafe(64)
            new_refresh_hash = UserSession.hash_token(new_raw_refresh)
        except Exception:
            logger.exception(
                "new_refresh_token_generation_failed",
                extra={"session_id": str(session_id)},
            )
            return Response(
                {
                    "code": "REFRESH_INTERNAL_ERROR",
                    "detail": "Internal server error.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            with transaction.atomic():
                try:
                    session = (
                        UserSession.objects
                        # Lock only UserSession. user__active_role may require
                        # an OUTER JOIN because active_role is nullable.
                        .select_for_update(of=("self",))
                        .select_related("user", "user__active_role")
                        .get(id=session_id)
                    )
                except UserSession.DoesNotExist:
                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                if session.status != UserSession.Status.ACTIVE:
                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                is_current_token = secrets.compare_digest(
                    session.refresh_token_hash,
                    hashed_refresh,
                )
                is_previous_token = bool(
                    session.previous_refresh_token_hash
                ) and secrets.compare_digest(
                    session.previous_refresh_token_hash,
                    hashed_refresh,
                )

                # The selector identifies a row, but only the matching cookie
                # proves possession of that session's refresh credential.
                if not is_current_token and not is_previous_token:
                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                same_user_agent = (
                    not session.user_agent_hash
                    or session.user_agent_hash == request_user_agent_hash
                )

                if is_previous_token and not same_user_agent:
                    self._revoke_family(
                        session,
                        reason="refresh_token_reuse_user_agent_mismatch",
                    )
                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                if is_previous_token:
                    within_grace = (
                        session.last_used_at is not None
                        and now - session.last_used_at <= grace_period
                    )

                    if within_grace and same_user_agent:
                        return self._refresh_conflict_response(session_id)

                    self._revoke_family(
                        session,
                        reason="refresh_token_reuse",
                    )
                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                if not same_user_agent:
                    session.status = UserSession.Status.REVOKED
                    session.save(update_fields=["status"])

                    AuditLog.objects.create(
                        event_type=AuditLog.Events.SESSION_REVOKED,
                        user=session.user,
                        user_public_id=str(session.user.public_id),
                        user_email=session.user.email,
                        metadata={
                            "reason": "user_agent_mismatch",
                            "session_id": str(session.id),
                        },
                    )

                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                if (
                    session.absolute_expires_at <= now
                    or session.expires_at <= now
                ):
                    session.status = UserSession.Status.EXPIRED
                    session.save(update_fields=["status"])

                    AuditLog.objects.create(
                        event_type=AuditLog.Events.SESSION_EXPIRED,
                        user=session.user,
                        user_public_id=str(session.user.public_id),
                        user_email=session.user.email,
                        metadata={"session_id": str(session.id)},
                    )

                    return self._invalid_session_response(
                        cookie_name=cookie_name,
                    )

                user = session.user

                if user.is_locked:
                    UserSession.objects.filter(
                        user=user,
                        status=UserSession.Status.ACTIVE,
                    ).update(status=UserSession.Status.REVOKED)

                    AuditLog.objects.create(
                        event_type=AuditLog.Events.SESSION_REVOKED,
                        user=user,
                        user_public_id=str(user.public_id),
                        user_email=user.email,
                        metadata={
                            "reason": "account_locked",
                            "session_id": str(session.id),
                        },
                    )

                    response = Response(
                        {
                            "code": "ACCOUNT_LOCKED",
                            "detail": (
                                "Your account has been locked. "
                                "Please contact your administrator."
                            ),
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                    response.delete_cookie(cookie_name, path="/")
                    return response

                # Rotate only the selected row while it remains locked.
                session.previous_refresh_token_hash = (
                    session.refresh_token_hash
                )
                session.refresh_token_hash = new_refresh_hash
                session.expires_at = now + get_session_idle_timeout()
                session.last_ip_address = ip_address
                session.last_used_at = now

                session.save(
                    update_fields=[
                        "previous_refresh_token_hash",
                        "refresh_token_hash",
                        "expires_at",
                        "last_ip_address",
                        "last_used_at",
                    ]
                )

                access_token = AccessToken.for_user(user)
                access_token.set_exp(
                    lifetime=get_access_token_lifetime(),
                )
                access_token["public_id"] = str(user.public_id)
                access_token["session_id"] = str(session.id)
                access_token["idle_exp"] = int(
                    session.expires_at.timestamp()
                )
                access_token["abs_exp"] = int(
                    session.absolute_expires_at.timestamp()
                )
                access_token["role_id"] = (
                    user.active_role.public_id
                    if user.active_role
                    else None
                )

                response = Response(
                    {
                        "access": str(access_token),
                        "session_id": str(session.id),
                        "public_id": str(user.public_id),
                        "role_id": (
                            user.active_role.public_id
                            if user.active_role
                            else None
                        ),
                    },
                    status=status.HTTP_200_OK,
                )

                response.set_cookie(
                    key=cookie_name,
                    value=new_raw_refresh,
                    httponly=True,
                    secure=settings.SESSION_COOKIE_SECURE,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                    path="/",
                    max_age=max(
                        0,
                        int(
                            (
                                session.absolute_expires_at - now
                            ).total_seconds()
                        ),
                    ),
                )

                response.delete_cookie(
                    LEGACY_REFRESH_COOKIE_NAME,
                    path="/",
                )

                return response

        except Exception:
            logger.exception(
                "refresh_flow_failed",
                extra={
                    "session_id": str(session_id),
                    "has_refresh_cookie": bool(raw_refresh),
                },
            )

            return Response(
                {
                    "code": "REFRESH_INTERNAL_ERROR",
                    "detail": "Internal server error.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutAPIView(APIView):
    """Revoke and clear only the session selected by X-Session-ID."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @staticmethod
    def get_client_ip(request) -> str | None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _success_response(
        *,
        session_id: uuid.UUID,
        cookie_name: str,
    ) -> Response:
        response = Response(
            {
                "detail": "Successfully logged out.",
                "session_id": str(session_id),
            },
            status=status.HTTP_200_OK,
        )
        response.delete_cookie(cookie_name, path="/")
        return response

    def post(self, request):
        session_id = parse_session_id(request)

        if session_id is None:
            return Response(
                {
                    "code": "INVALID_SESSION_ID",
                    "detail": (
                        f"A valid {SESSION_ID_HEADER} header is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cookie_name = refresh_cookie_name(session_id)
        raw_refresh = request.COOKIES.get(cookie_name)

        # Logout is idempotent, but the session selector alone is never enough
        # to revoke a row. Without the matching cookie, only clear that cookie
        # name from the browser and report success.
        if not raw_refresh:
            return self._success_response(
                session_id=session_id,
                cookie_name=cookie_name,
            )

        try:
            hashed_refresh = UserSession.hash_token(raw_refresh)
        except Exception:
            logger.exception(
                "logout_refresh_token_hashing_failed",
                extra={
                    "session_id": str(session_id),
                    "has_refresh_cookie": True,
                },
            )
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        ip = self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]
        session = None
        revoked_now = False

        try:
            with transaction.atomic():
                try:
                    session = (
                        UserSession.objects
                        .select_for_update(of=("self",))
                        .select_related("user")
                        .get(id=session_id)
                    )
                except UserSession.DoesNotExist:
                    return self._success_response(
                        session_id=session_id,
                        cookie_name=cookie_name,
                    )

                current_matches = secrets.compare_digest(
                    session.refresh_token_hash,
                    hashed_refresh,
                )
                previous_matches = bool(
                    session.previous_refresh_token_hash
                ) and secrets.compare_digest(
                    session.previous_refresh_token_hash,
                    hashed_refresh,
                )

                # A known selector with the wrong cookie does not authorize
                # revocation. Preserve idempotent logout semantics without
                # affecting any other session.
                if not current_matches and not previous_matches:
                    return self._success_response(
                        session_id=session_id,
                        cookie_name=cookie_name,
                    )

                if session.status == UserSession.Status.ACTIVE:
                    session.status = UserSession.Status.REVOKED
                    session.last_ip_address = ip
                    session.save(
                        update_fields=["status", "last_ip_address"]
                    )
                    revoked_now = True

        except Exception:
            logger.exception(
                "logout_session_revoke_failed",
                extra={"session_id": str(session_id)},
            )
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if session is not None and revoked_now:
            try:
                AuditLog.objects.create(
                    event_type=AuditLog.Events.LOGOUT,
                    user=session.user,
                    user_public_id=str(session.user.public_id),
                    user_email=session.user.email,
                    ip_address=ip,
                    user_agent=user_agent,
                    metadata={"session_id": str(session.id)},
                )
            except Exception:
                logger.warning(
                    "logout_audit_log_failed",
                    extra={
                        "user_id": session.user_id,
                        "session_id": str(session.id),
                    },
                )

        return self._success_response(
            session_id=session_id,
            cookie_name=cookie_name,
        )


class PasswordResetRequestView(AuditMixin, APIView):

    # throttle_classes = [PasswordResetThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = serializer.save()

        if event:
            self.audit(
                event_type=AuditLog.Events.PASSWORD_RESET_REQUESTED,
                target=event.user,
                description="Password reset requested",
            )

        return Response(
            {"detail": "If an account exists, a password reset email has been sent."},
            status=200,
        )

class PasswordResetConfirmView(AuditMixin, APIView):
    """
    Confirm password reset (user or admin triggered) and set new password.
    """

    permission_classes = [AllowAny] 

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)


        user = serializer.save()

        self.audit(
            event_type=AuditLog.Events.PASSWORD_RESET_COMPLETED,
            target=user,
            description="Password reset completed successfully",
        )

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )
    
class PasswordResetValidateView(APIView):
    """Validate password reset token."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {"code": "TOKEN_MISSING", "detail": "No token provided."},
                status=400,
            )

        token_service = PasswordResetToken()
        event, status = token_service.verify_token(token)

        if status == "expired":
            return Response(
                {
                    "code": "TOKEN_EXPIRED",
                    "detail": "This password reset link has expired.",
                },
                status=400,
            )

        if status != "valid":
            return Response(
                {
                    "code": "TOKEN_INVALID",
                    "detail": "This password reset link is invalid.",
                },
                status=400,
            )

        # Token is valid
        return Response(
            {
                "code": "SUCCESS",
                "detail": "Token is valid.",
            },
            status=200,
        )

