from rest_framework_simplejwt.views import TokenObtainPairView
from ..serializers.general import SessionTokenLoginViewSerializer
from ..serializers.equipment import EquipmentBatchtWriteSerializer
from ..serializers.consumables import ConsumableBatchWriteSerializer
from ..serializers.accessories import AccessoryBatchWriteSerializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..models import UserSession
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.views import APIView
from ..utils import get_serializer_field_info
from rest_framework.serializers import Serializer


class SessionTokenLoginView(TokenObtainPairView):
    serializer_class = SessionTokenLoginViewSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Authenticate user via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        #Access token (JWT)
        access_token = str(AccessToken.for_user(user))

        # Opaque refresh token
        import secrets
        raw_refresh = secrets.token_urlsafe(64)
        hashed_refresh = UserSession.hash_token(raw_refresh)

       # Save session first
        session = UserSession.objects.create(
            user=user,
            refresh_token_hash=hashed_refresh,
            expires_at=timezone.localtime(timezone.now()) + timedelta(days=1),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # Access token (JWT) bound to session
        access_token_obj = AccessToken.for_user(user)
        access_token_obj["session_id"] = str(session.id)
        access_token = str(access_token_obj)

        # Build response including metadata
        response_data = {
            "access": access_token,
            "public_id": str(user.public_id),
            "role_id": user.active_role.public_id if user.active_role else None,
        }

        # Set refresh token as HttpOnly cookie
        response = Response(response_data, status=200)
        response.set_cookie(
            key="refresh",
            value=raw_refresh,
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )

        return response

class RefreshAPIView(APIView):
    permission_classes = [AllowAny]          
    authentication_classes = []              

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh")
        if not raw_refresh:
            return Response({"detail": "No refresh token found."}, status=status.HTTP_400_BAD_REQUEST)

        hashed_refresh = UserSession.hash_token(raw_refresh)

        try:
            session = UserSession.objects.get(
                refresh_token_hash=hashed_refresh,
                status=UserSession.Status.ACTIVE,
                expires_at__gt=timezone.now()
            )
        except UserSession.DoesNotExist:
            return Response({"detail": "Invalid or expired session."}, status=status.HTTP_401_UNAUTHORIZED)

        # Issue new access token
        user = session.user
        access_token = AccessToken.for_user(user)
        access_token["public_id"] = str(user.public_id)
        access_token["session_id"] = str(session.id)
        access_token["role_id"] = user.active_role.public_id if user.active_role else None

        # Optionally rotate refresh token
        import secrets
        new_raw_refresh = secrets.token_urlsafe(64)
        session.refresh_token_hash = UserSession.hash_token(new_raw_refresh)
        session.expires_at = timezone.now() + timedelta(days=7)  # reset expiry
        session.save(update_fields=["refresh_token_hash", "expires_at"])

        response = Response(
            {
                "access": str(access_token),
                "public_id": str(user.public_id),
                "role_id": user.active_role.public_id if user.active_role else None,
            },
            status=status.HTTP_200_OK
        )
        # Set new refresh token in HttpOnly cookie
        response.set_cookie(
            key="refresh",
            value=new_raw_refresh,
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )
        return response

class LogoutAPIView(APIView):
    permission_classes = [AllowAny]          
    authentication_classes = []              

    def post(self, request):
        # Get refresh token from HttpOnly cookie
        raw_refresh = request.COOKIES.get("refresh")
        if not raw_refresh:
            return Response({"detail": "No refresh token found."}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session in DB
        hashed_refresh = UserSession.hash_token(raw_refresh)
        try:
            session = UserSession.objects.get(refresh_token_hash=hashed_refresh)
            session.status = UserSession.Status.REVOKED
            session.save(update_fields=["status"])
        except UserSession.DoesNotExist:
            # Token not found or already revoked/expired
            return Response({"detail": "Invalid or expired session."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete cookie
        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
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
    