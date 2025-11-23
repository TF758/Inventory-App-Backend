from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import hashlib
import secrets
from django.utils import timezone
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from rest_framework.views import APIView
from db_inventory.models import PasswordResetEvent , UserSession, User
from db_inventory.serializers.auth import TempPasswordChangeSerializer, ChangePasswordSerializer
from rest_framework import permissions


class RevokeUserSessionsViewset(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    """
    Custom ViewSet for revoking sessions.
    """
    queryset = UserSession.objects.all()

    @action(detail=False, methods=["post"], url_path="revoke-all")
    def revoke_all(self, request):
        """
        POST /api/sessions/revoke-all/
        Body: {"public_id": "xyz123"}

        Revokes all ACTIVE sessions for the target user.
        """
        public_id = request.data.get("public_id")
        if not public_id:
            return Response({"detail": "public_id is required."}, status=400)

        user = get_object_or_404(User, public_id=public_id)

        # Revoke only ACTIVE sessions (recommended)
        sessions = UserSession.objects.filter(
            user=user,
            status=UserSession.Status.ACTIVE
        )

        revoked_count = sessions.update(status=UserSession.Status.REVOKED)

        return Response(
            {
                "public_id": public_id,
                "revoked_count": revoked_count,
                "message": f"Revoked {revoked_count} sessions for user."
            },
            status=status.HTTP_200_OK
        )


class UserLockViewSet(viewsets.GenericViewSet):
    """
    Admin-only ViewSet to lock or unlock user accounts.
    Locking automatically revokes all active sessions.
    """
    queryset = User.objects.all()
   
    lookup_field = "public_id"

    @action(detail=True, methods=["post"])
    def lock(self, request, public_id=None):
        user = get_object_or_404(User, public_id=public_id)
        if user.is_locked:
            return Response({"detail": "User account is already locked."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Lock the account
        user.is_locked = True
        user.save(update_fields=["is_locked"])

        # Revoke all active sessions
        UserSession.objects.filter(user=user, status=UserSession.Status.ACTIVE).update(
            status=UserSession.Status.REVOKED
        )

        return Response({"detail": f"User {user.email} has been locked and logged out."},
                        status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def unlock(self, request, public_id=None):
        user = get_object_or_404(User, public_id=public_id)
        if not user.is_locked:
            return Response({"detail": "User account is not locked."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Unlock the account
        user.is_locked = False
        user.save(update_fields=["is_locked"])

        return Response({"detail": f"User {user.email} has been unlocked."},
                        status=status.HTTP_200_OK)


class AdminResetUserPasswordView(APIView):
    """
    Admin triggers a password reset for a user using public_id.
    Sends email and also returns temp password to admin in case email fails.
    """
    

    def post(self, request, user_public_id):
        try:
            user = User.objects.get(public_id=user_public_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Generate a temporary password
        temp_password = secrets.token_urlsafe(8)  # ~12 chars
        temp_password_hash = hashlib.sha256(temp_password.encode()).hexdigest()

        # Create reset event
        expires_at = timezone.now() + timezone.timedelta(hours=1)
        event = PasswordResetEvent.objects.create(
            user=user,
            admin=request.user,
            temp_password_hash=temp_password_hash,
            expires_at=expires_at
        )

        # Flag the user to force password change
        user.force_password_change = True
        user.save(update_fields=["force_password_change"])

        # Send email (optional; fallback is admin manual delivery)
        try:
            send_mail(
                subject="Your Temporary Password",
                message=f"Your temporary password is: {temp_password}\nIt expires at {expires_at}.",
                from_email="noreply@example.com",
                recipient_list=[user.email],
            )
        except Exception:
            # Log email failure, fallback to manual delivery
            pass

        # Return temp password to admin for manual delivery if needed
        return Response({
            "detail": "Temporary password created and email sent (if delivery succeeded).",
            "temp_password": temp_password  # only visible to admin
        }, status=status.HTTP_200_OK)
    

class TempPasswordLoginView(APIView):
    """
    User logs in with a temporary password and is required to set a new password.
    """

    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data.get("email")
        serializer = TempPasswordChangeSerializer(data=request.data, context={"email": email})
        serializer.is_valid(raise_exception=True)

        event = serializer.validated_data["reset_event"]
        user = event.user
        new_password = serializer.validated_data["new_password"]

        # Update user password and clear force_password_change
        user.set_password(new_password)
        user.force_password_change = False
        user.save(update_fields=["password", "force_password_change"])

        # Mark event as used
        event.used_at = timezone.now()
        event.save(update_fields=["used_at"])

        return Response({"detail": "Password changed successfully, you may now log in with the new password."})
    

class ChangePasswordView(APIView):

    """Allows an authneticated user to change thier password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Change password
            serializer.save()

            # Revoke all user sessions (security measure)
            UserSession.objects.filter(user=request.user, status=UserSession.Status.ACTIVE).update(
                status=UserSession.Status.REVOKED
            )

        response = Response(
            {"detail": "Password changed successfully. All sessions have been logged out."},
            status=status.HTTP_200_OK,
        )

        # Optionally clear the refresh cookie
        response.delete_cookie("refresh", path="/")

        return response