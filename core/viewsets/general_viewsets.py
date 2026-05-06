import token
from rest_framework_simplejwt.views import TokenObtainPairView
from core.serializers.general import SessionTokenLoginViewSerializer, PasswordResetRequestSerializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from core.models.sessions import UserSession
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.views import APIView
import secrets
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException
from core.utils.tokens import PasswordResetToken
from core.serializers.auth import PasswordResetConfirmSerializer
from core.throttling import LoginThrottle, PasswordResetThrottle, RefreshTokenThrottle
from rest_framework.exceptions import Throttled
from core.mixins import AuditMixin
from core.models.audit import AuditLog
from django.db.models import Q
from django.conf import settings
from core.security_policy import *
from core.logging import get_logger


logger = get_logger(__name__)

class SessionTokenLoginView(TokenObtainPairView):
    serializer_class = SessionTokenLoginViewSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        ip = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]

        # -------------------------
        # Authenticate user
        # -------------------------
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            AuditLog.objects.create(
                event_type=AuditLog.Events.LOGIN_FAILED,
                description="Login failed",
                metadata={"reason": str(exc)},
                ip_address=ip,
                user_agent=user_agent,
            )
            raise

        user = serializer.user
        now = timezone.now()

        # -------------------------
        # Generate refresh token
        # -------------------------
        raw_refresh = secrets.token_urlsafe(64)

        try:
            hashed_refresh = UserSession.hash_token(raw_refresh)
        except Exception:
            logger.exception(
                "refresh_token_hashing_failed",
                extra={
                    "user_id": user.pk,
                    "has_user_agent": bool(user_agent),
                },
            )
            raise APIException("Authentication failed.")

        # -------------------------
        # Create session (atomic)
        # -------------------------
        try:
            with transaction.atomic():

                ua_hash = UserSession.hash_user_agent(user_agent)
                device_name = request.headers.get("X-Device-Name")

                # Load security policy
                policy = SecuritySettings.load()

                # Enforce max concurrent sessions
                active_sessions = UserSession.objects.filter(
                    user=user,
                    status=UserSession.Status.ACTIVE,
                ).order_by("created_at")

                if active_sessions.count() >= policy.max_concurrent_sessions:
                    oldest_session = active_sessions.first()
                    if oldest_session:
                        oldest_session.status = UserSession.Status.REVOKED
                        oldest_session.save(update_fields=["status"])

                        AuditLog.objects.create(
                            event_type=AuditLog.Events.SESSION_REVOKED,
                            user=user,
                            user_public_id=str(user.public_id),
                            user_email=user.email,
                            metadata={"reason": "max_concurrent_sessions"},
                        )

                session = UserSession.objects.create(
                    user=user,
                    refresh_token_hash=hashed_refresh,
                    device_name=device_name,
                    last_ip_address=ip,
                    expires_at=now + get_session_idle_timeout(),
                    absolute_expires_at=now + get_session_absolute_lifetime(),
                    user_agent_hash=ua_hash,
                    ip_address=ip,
                )

        except Exception:
            logger.exception(
                "session_creation_failed",
                extra={
                    "user_id": user.pk,
                    "active_sessions_count": active_sessions.count(),
                    "max_sessions": policy.max_concurrent_sessions,
                },
            )
            raise APIException("Authentication failed.")

        # -------------------------
        # Generate access token
        # -------------------------
        try:
            raise Exception ("This is a bad login test")
            access_token_obj = AccessToken.for_user(user)

            access_token_obj.set_exp(
                lifetime=get_access_token_lifetime()
            )

            access_token_obj["session_id"] = str(session.id)
            access_token_obj["abs_exp"] = int(session.absolute_expires_at.timestamp())
            access_token_obj["idle_exp"] = int(session.expires_at.timestamp())

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
            raise APIException("Authentication failed.")

        # -------------------------
        # Update last login
        # -------------------------
        user.last_login = now
        user.save(update_fields=["last_login"])

        # -------------------------
        # Successful login audit
        # -------------------------
        AuditLog.objects.create(
            event_type=AuditLog.Events.LOGIN,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
            ip_address=ip,
            user_agent=user_agent,
        )

        # -------------------------
        # Response
        # -------------------------
        response_data = {
            "access": access_token,
            "public_id": str(user.public_id),
            "role_id": user.active_role.public_id if user.active_role else None,
            "force_password_change": user.force_password_change,
        }

        response = Response(response_data, status=status.HTTP_200_OK)

        response.set_cookie(
            key="refresh",
            value=raw_refresh,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
            max_age=int(get_session_absolute_lifetime().total_seconds()),
        )

        return response   
    
class RefreshAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RefreshTokenThrottle]

    def get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def post(self, request):

        try:
            raw_refresh = request.COOKIES.get("refresh")

            if not raw_refresh:
                return Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            hashed_refresh = UserSession.hash_token(raw_refresh)

            ip = self.get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]

            # ----------------------------------------
            # Locate session
            # ----------------------------------------
            try:
                session = UserSession.objects.get(
                    Q(refresh_token_hash=hashed_refresh)
                    | Q(previous_refresh_token_hash=hashed_refresh),
                    status=UserSession.Status.ACTIVE,
                )
            except UserSession.DoesNotExist:
                return Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            now = timezone.now()

            # ----------------------------------------
            # Refresh token reuse detection
            # ----------------------------------------
            if session.previous_refresh_token_hash == hashed_refresh:

                # revoke entire family
                UserSession.objects.filter(
                    session_family=session.session_family
                ).update(status=UserSession.Status.REVOKED)

                AuditLog.objects.create(
                    event_type=AuditLog.Events.SESSION_REVOKED,
                    user=session.user,
                    metadata={"reason": "refresh_token_reuse", "family": str(session.session_family)},
                )

                resp = Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                resp.delete_cookie("refresh", path="/")
                return resp

            # ----------------------------------------
            # Expiration checks
            # ----------------------------------------
            if session.absolute_expires_at <= now or session.expires_at <= now:

                session.status = UserSession.Status.EXPIRED
                session.save(update_fields=["status"])

                AuditLog.objects.create(
                    event_type=AuditLog.Events.SESSION_EXPIRED,
                    user=session.user,
                    user_public_id=str(session.user.public_id),
                    user_email=session.user.email,
                )

                resp = Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                resp.delete_cookie("refresh", path="/")
                return resp

            # ----------------------------------------
            # User-agent binding
            # ----------------------------------------
            req_ua_hash = UserSession.hash_user_agent(user_agent)

            if session.user_agent_hash and session.user_agent_hash != req_ua_hash:

                session.status = UserSession.Status.REVOKED
                session.save(update_fields=["status"])

                AuditLog.objects.create(
                    event_type=AuditLog.Events.SESSION_REVOKED,
                    user=session.user,
                    metadata={"reason": "user_agent_mismatch"},
                )

                resp = Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                resp.delete_cookie("refresh", path="/")
                return resp

            user = session.user

            # ----------------------------------------
            # Locked account handling
            # ----------------------------------------
            if user.is_locked:

                UserSession.objects.filter(
                    user=user,
                    status=UserSession.Status.ACTIVE,
                ).update(status=UserSession.Status.REVOKED)

                AuditLog.objects.create(
                    event_type=AuditLog.Events.SESSION_REVOKED,
                    user=user,
                    metadata={"reason": "account_locked"},
                )

                resp = Response(
                    {
                        "detail": "Your account has been locked. Please contact your administrator."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

                resp.delete_cookie("refresh", path="/")
                return resp

            # ----------------------------------------
            # Rotate refresh token
            # ----------------------------------------
            new_raw_refresh = secrets.token_urlsafe(64)
            new_hash = UserSession.hash_token(new_raw_refresh)

            try:
                with transaction.atomic():

                    session.previous_refresh_token_hash = session.refresh_token_hash
                    session.refresh_token_hash = new_hash

                    # refresh idle timeout
                    session.expires_at = now + get_session_idle_timeout()

                    # update session activity metadata
                    session.last_ip_address = ip

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

            except Exception:
                logger.exception(
                    "refresh_token_rotation_failed",
                    extra={
                        "session_id": str(session.id),
                        "user_id": session.user_id,
                    },
                )
                return Response(
                    {"detail": "Internal server error."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # ----------------------------------------
            # Generate access token
            # ----------------------------------------
            try:
                access_token = AccessToken.for_user(user)
                access_token.set_exp(lifetime=get_access_token_lifetime())

            except Exception:
                logger.exception(
                    "access_token_generation_failed",
                    extra={
                        "session_id": str(session.id),
                        "user_id": user.pk,
                    },
                )
                return Response(
                    {"detail": "Internal server error."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            access_token["public_id"] = str(user.public_id)
            access_token["session_id"] = str(session.id)
            access_token["idle_exp"] = int(session.expires_at.timestamp())
            access_token["abs_exp"] = int(session.absolute_expires_at.timestamp())
            access_token["role_id"] = (
                user.active_role.public_id if user.active_role else None
            )

            # ----------------------------------------
            # Response
            # ----------------------------------------
            response = Response(
                {
                    "access": str(access_token),
                    "public_id": str(user.public_id),
                    "role_id": (
                        user.active_role.public_id if user.active_role else None
                    ),
                },
                status=status.HTTP_200_OK,
            )

            response.set_cookie(
                key="refresh",
                value=new_raw_refresh,
                httponly=True,
                secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE,
                path="/",
                max_age=int(get_session_absolute_lifetime().total_seconds()),
            )

            return response

        except Exception:
            logger.exception(
                "refresh_flow_failed",
                extra={
                    "has_refresh_cookie": bool(request.COOKIES.get("refresh")),
                },
            )

            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
class LogoutAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def post(self, request):

        raw_refresh = request.COOKIES.get("refresh")

        if not raw_refresh:
            response = Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
            response.delete_cookie("refresh", path="/")
            return response

        try:
            hashed_refresh = UserSession.hash_token(raw_refresh)
        except Exception:
            logger.exception(
                "logout_refresh_token_hashing_failed",
                extra={
                    "has_refresh_cookie": bool(raw_refresh),
                },
            )
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        ip = self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]

        try:
            with transaction.atomic():

                session = UserSession.objects.select_for_update().get(
                    Q(refresh_token_hash=hashed_refresh)
                    | Q(previous_refresh_token_hash=hashed_refresh)
                )

                # Idempotent logout
                if session.status != UserSession.Status.ACTIVE:
                    response = Response(
                        {"detail": "Successfully logged out."},
                        status=status.HTTP_200_OK,
                    )
                    response.delete_cookie("refresh", path="/")
                    return response

                session.status = UserSession.Status.REVOKED
                session.last_ip_address = ip
                session.save(update_fields=["status", "last_ip_address"])

        except UserSession.DoesNotExist:
            response = Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
            response.delete_cookie("refresh", path="/")
            return response

        except Exception:
            logger.exception(
                "logout_session_revoke_failed",
                extra={
                    "session_id": str(getattr(session, "id", None)),
                },
            )
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Audit log
        try:
            AuditLog.objects.create(
                event_type=AuditLog.Events.LOGOUT,
                user=session.user,
                user_public_id=str(session.user.public_id),
                user_email=session.user.email,
                ip_address=ip,
                user_agent=user_agent,
            )
        except Exception:
            logger.warning(
            "logout_audit_log_failed",
            extra={
                "user_id": session.user_id,
                "session_id": str(session.id),
            },
        )

        response = Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )

        response.delete_cookie("refresh", path="/")

        return response


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

