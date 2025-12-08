from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from db_inventory.models import UserSession, User, AuditLog
from db_inventory.serializers.auth import ChangePasswordSerializer, AdminPasswordResetSerializer, AuditLogLightSerializer, AuditLogSerializer
from rest_framework import permissions
from db_inventory.pagination import FlexiblePagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import AuditLogFilter
from db_inventory.mixins import ScopeFilterMixin


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
    Sends an email with a token-based reset link.
    """
    def post(self, request, user_public_id):
        serializer = AdminPasswordResetSerializer(
            data={"user_public_id": user_public_id}
        )
        serializer.is_valid(raise_exception=True)
        
        reset_link = serializer.save(admin=request.user)

        return Response(
            {
                "detail": "Password reset link sent to user.",
                "reset_link": reset_link  # Optional: admin may see it
            },
            status=status.HTTP_200_OK
        )
    

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
    

class AuditLogViewSet(ScopeFilterMixin,viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit log listing with department/location scoping.
    Department admins only see logs belonging to their assigned department.
    """
    queryset = AuditLog.objects.all().select_related(
        "department", "location", "room"
    )
    serializer_class = AuditLogLightSerializer
    pagination_class = FlexiblePagination

    # Filtering + search
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^user_email', 'user_email']
    filterset_class = AuditLogFilter

    # Filters
    filterset_fields = [
        "event_type",
        "target_model",
        "department_name",
        "location_name",
        "room_name",
        "user",
    ]

    # Search
    search_fields = [
        "target_id",
        "target_name",
        "description",
        "user__email",
        "event_type",
        "department_name",
        "location_name",
        "room_name",
    ]

    # Ordering
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()

        user = self.request.user

        # --- Department-based scoping ---
        # If your user model has a department assignment:
        if hasattr(user, "department") and user.department:
            return qs.filter(department=user.department)

        # Superusers see everything
        if user.is_superuser:
            return qs

        # Fallback: normal users only see logs generated by themselves
        return qs.filter(user=user)