import token
from rest_framework_simplejwt.views import TokenObtainPairView
from db_inventory.serializers.general import SessionTokenLoginViewSerializer, PasswordResetRequestSerializer
from db_inventory.serializers.equipment import EquipmentBatchtWriteSerializer
from db_inventory.serializers.consumables import ConsumableBatchWriteSerializer
from db_inventory.serializers.accessories import AccessoryBatchWriteSerializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from db_inventory.models.security import UserSession
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.views import APIView
from db_inventory.utils.serializers import get_serializer_field_info
from rest_framework.serializers import Serializer
import logging
import secrets
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException
from db_inventory.utils.tokens import PasswordResetToken
from db_inventory.serializers.auth import PasswordResetConfirmSerializer
from db_inventory.throttling import LoginThrottle, PasswordResetThrottle, RefreshTokenThrottle
from rest_framework.exceptions import Throttled
from db_inventory.mixins import AuditMixin
from db_inventory.models.audit import AuditLog
from django.db.models import Q
from django.conf import settings
from db_inventory.security_policy import *



logger = logging.getLogger(__name__) 

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
                "Refresh token hashing failed",
                extra={"user_id": user.pk},
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
                "Session creation failed",
                extra={"user_id": user.pk},
            )
            raise APIException("Authentication failed.")

        # -------------------------
        # Generate access token
        # -------------------------
        try:
            access_token_obj = AccessToken.for_user(user)

            access_token_obj.set_exp(
                lifetime=get_access_token_lifetime()
            )

            access_token_obj["session_id"] = str(session.id)
            access_token_obj["abs_exp"] = int(session.absolute_expires_at.timestamp())
            access_token_obj["idle_exp"] = int(session.expires_at.timestamp())

            access_token = str(access_token_obj)

        except Exception:
            session.delete()

            logger.exception(
                "Access token generation failed",
                extra={"user_id": user.pk},
            )
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
                    "Refresh token rotation failed",
                    extra={"session_id": str(session.id)},
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
                    "Access token generation failed",
                    extra={"session_id": str(session.id)},
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
            logger.exception("Refresh flow failed")

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
            logger.exception("Logout refresh token hashing failed")
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
                "Logout session revoke failed",
                extra={"session_id": str(session.id)},
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
            logger.warning("Logout audit log failed")

        response = Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )

        response.delete_cookie("refresh", path="/")

        return response

def get_serializer_field_info(serializer_class: Serializer):
        """Return cleaned up metadata for serializer fields"""
        serializer = serializer_class()

        field_info = {}
        for field_name, field in serializer.fields.items():
            field_info[field_name] = {
                "label": field.label or field_name.replace("_", " ").title(),
                "type": field.__class__.__name__,
                "required": field.required,
                "read_only": field.read_only,
                "write_only": field.write_only,
                "help_text": field.help_text or "",
                "max_length": getattr(field, "max_length", None),
            }
        return field_info

class SerializerFieldsView(APIView):

    """Used to return data about a model field using it's respective serializer in batch processes"""
    """
    Return field metadata for a given model serializer.
    Pass `serializer_name` as query param (e.g., EquipmentBatchWriteSerializer)
    """

    serializer_map = {
        "equipment": EquipmentBatchtWriteSerializer,
        "consumable": ConsumableBatchWriteSerializer,
        "accessory": AccessoryBatchWriteSerializer,
    }

    def get(self, request):
        serializer_key = request.query_params.get("serializer")
        if not serializer_key:
            return Response(
                {"error": "Query param 'serializer' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer_class = self.serializer_map.get(serializer_key.lower())
        if not serializer_class:
            return Response(
                {"error": f"No serializer found for '{serializer_key}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(get_serializer_field_info(serializer_class))

class PasswordResetRequestView(AuditMixin, APIView):

    # throttle_classes = [PasswordResetThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

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
        serializer.save()

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

