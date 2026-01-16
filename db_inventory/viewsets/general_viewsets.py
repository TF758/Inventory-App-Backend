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
from datetime import timedelta
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

IDLE_TIMEOUT = timedelta(seconds=60)
ABSOLUTE_LIFETIME = timedelta(seconds=120)

logger = logging.getLogger(__name__) 

class SessionTokenLoginView(TokenObtainPairView):
    serializer_class = SessionTokenLoginViewSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]


    def post(self, request, *args, **kwargs):
        # Authenticate user via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Will automatically raise ForcePasswordChangeException if needed
        user = serializer.user

        # Generate opaque refresh token (raw) and its hash
        raw_refresh = secrets.token_urlsafe(64)
        try:
            hashed_refresh = UserSession.hash_token(raw_refresh)
        except Exception:
            logger.exception("Refresh token hashing failed", extra={"user_id": user.pk})
            raise APIException("Authentication failed.")
        
        now = timezone.now()

        # Create session and ensure atomicity — if anything after creation fails, we will remove the session
        try:
            with transaction.atomic():
                ua_hash = UserSession.hash_user_agent(
                    request.META.get("HTTP_USER_AGENT", "")
                )
                session = UserSession.objects.create(
                user=user,
                refresh_token_hash=hashed_refresh,
                expires_at= now + IDLE_TIMEOUT,
                absolute_expires_at=now + ABSOLUTE_LIFETIME,
                user_agent_hash=ua_hash,  
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            logger.exception("Session creation failed", extra={"user_id": user.pk})
            raise APIException("Authentication failed.")

        # Generate access token bound to the created session.
        try:
            access_token_obj = AccessToken.for_user(user)
            access_token_obj["session_id"] = str(session.id)
            access_token_obj["abs_exp"] = int(session.absolute_expires_at.timestamp())
            access_token_obj["idle_exp"] = int(session.expires_at.timestamp())
            access_token = str(access_token_obj)
        except Exception:
                session.delete()
                logger.exception("Access token generation failed", extra={"user_id": user.pk})
                raise APIException("Authentication failed.")

        # Build response including metadata
        response_data = {
            "access": access_token,
            "public_id": str(user.public_id),
            "role_id": user.active_role.public_id if user.active_role else None,
        }

        # Set refresh token as HttpOnly cookie only after everything succeeded
        response = Response(response_data, status=200)
        response.set_cookie(
            key="refresh",
            value=raw_refresh,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
            max_age=int(ABSOLUTE_LIFETIME.total_seconds()),
        )

        return response
    
class RefreshAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RefreshTokenThrottle]

    def post(self, request):
        try:
            # --- Get refresh token from cookie ---
            raw_refresh = request.COOKIES.get("refresh")
            if not raw_refresh:
                return Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            hashed_refresh = UserSession.hash_token(raw_refresh)

            # --- Lookup session (supports reuse detection) ---
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

            # --- Refresh token reuse detection ---
            if session.previous_refresh_token_hash == hashed_refresh:
                session.status = UserSession.Status.REVOKED
                session.save(update_fields=["status"])

                resp = Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                resp.delete_cookie("refresh", path="/")
                return resp

            now = timezone.now()

            # --- Absolute + idle expiration ---
            if session.absolute_expires_at <= now or session.expires_at <= now:
                session.status = UserSession.Status.EXPIRED
                session.save(update_fields=["status"])

                resp = Response(
                    {"detail": "Invalid or expired session."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                resp.delete_cookie("refresh", path="/")
                return resp

            # --- User-agent binding ---
            req_ua_hash = UserSession.hash_user_agent(
                request.META.get("HTTP_USER_AGENT", "")
            )
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

            # --- Locked account handling ---
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

            # --- Generate access token ---
            try:
                access_token = AccessToken.for_user(user)
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

            # --- Rotate refresh token 
            new_raw_refresh = secrets.token_urlsafe(64)
            new_hash = UserSession.hash_token(new_raw_refresh)

            try:
                with transaction.atomic():
                    session.previous_refresh_token_hash = session.refresh_token_hash
                    session.refresh_token_hash = new_hash
                    session.expires_at = now + IDLE_TIMEOUT
                    session.save(
                        update_fields=[
                            "previous_refresh_token_hash",
                            "refresh_token_hash",
                            "expires_at",
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

            # --- Success response ---
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
                max_age=int(ABSOLUTE_LIFETIME.total_seconds()),
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

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh")
        if not raw_refresh:
            return Response(
                {"detail": "No refresh token found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            hashed_refresh = UserSession.hash_token(raw_refresh)
        except Exception:
            logger.exception("Logout refresh token hashing failed")
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            session = UserSession.objects.get(
                Q(refresh_token_hash=hashed_refresh) |
                Q(previous_refresh_token_hash=hashed_refresh)
            )
        except UserSession.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔑 Idempotency check
        if session.status != UserSession.Status.ACTIVE:
            return Response(
                {"detail": "Invalid or expired session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session.status = UserSession.Status.REVOKED
            session.save(update_fields=["status"])
        except Exception:
            logger.exception("Logout session revoke failed")
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

    throttle_classes = [PasswordResetThrottle]

    """Initiate password reset by sending email with reset link."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = getattr(serializer, "user", None)

        if user:
            self.audit(
                event_type=AuditLog.Events.PASSWORD_RESET_REQUESTED,
                target=user,
                description="Password reset requested",
                metadata={
                    "initiated_by_admin": False,
                },
        )
        return Response({"detail": "If an account exists, a password reset email has been sent."}, status=200)

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

        payload = PasswordResetToken().verify_token(token)

        if payload is None:
            # Could be expired or invalid; we can distinguish based on internal checks
            return Response(
                {"code": "TOKEN_INVALID", "detail": "This password reset link is invalid or expired."},
                status=400,
            )

        # Token is valid → return success
        return Response({"status": "valid"}, status=200)


