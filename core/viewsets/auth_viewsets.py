from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from core.models import UserSession, AuditLog, SiteNameChangeHistory, SiteRelocationHistory
from core.serializers.auth import AdminSetTemporaryPasswordSerializer, ChangePasswordSerializer, AdminPasswordResetSerializer, AdminUserDemographicsSerializer, SecuritySettingsSerializer, SiteNameChangeHistoryListSerializer, SiteNameChangeHistorySerializer
from core.pagination import FlexiblePagination
from django_filters.rest_framework import DjangoFilterBackend
from core.mixins import AuditMixin, NotificationMixin
from rest_framework.exceptions import ValidationError, NotFound
from django.db import transaction
from core.permissions.users import AdminUpdateUserPermission
from core.utils.audit import create_audit_log
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from core.utils.viewset_helpers import get_users_affected_by_site
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from core.authentication import SessionJWTAuthentication
from django.utils import timezone
from datetime import timedelta
from core.security_policy import get_session_idle_timeout, invalidate_security_policy_cache
from core.models.notifications import Notification
from core.models.security import SecuritySettings
from core.filters import SiteNameChangeHistoryFilter
from core.serializers.audit import SiteNameChangeSerializer, SiteRelocationSerializer
from users.models.users import User
from sites.models.sites import Department, Location, Room


class SecuritySettingsAPIView(APIView):
    """
    Manage runtime security policy.

    GET   -> retrieve current policy
    PATCH -> update policy
    """

    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, _ = SecuritySettings.objects.get_or_create()
        return obj

    def get(self, request):
        policy = self.get_object()
        serializer = SecuritySettingsSerializer(policy)
        return Response(serializer.data)

    def patch(self, request):
        policy = self.get_object()

        serializer = SecuritySettingsSerializer(
            policy,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()

            invalidate_security_policy_cache()

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLockViewSet(AuditMixin, viewsets.GenericViewSet):
    """
    Admin-only ViewSet to lock or unlock user accounts.

    Locking:
    - revokes all active sessions
    - prevents future logins
    - blocks active authenticated sessions

    Unlocking:
    - clears all lock state
    - resets failed login tracking
    """

    queryset = User.objects.all()
    lookup_field = "public_id"

    @action(detail=True, methods=["post"])
    def lock(self, request, public_id=None):

        user = get_object_or_404(
            User,
            public_id=public_id,
        )

        if user.is_locked:

            return Response(
                {
                    "detail":
                    "User account is already locked."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get(
            "reason",
            "Locked by administrator",
        )

        # -----------------------------------------
        # Apply administrative lock
        # -----------------------------------------

        user.is_locked = True
        user.locked_reason = reason

        # Clear temporary lock state
        user.locked_until = None
        user.failed_login_attempts = 0
        user.last_failed_login_at = None

        user.save(update_fields=[
            "is_locked",
            "locked_reason",
            "locked_until",
            "failed_login_attempts",
            "last_failed_login_at",
        ])

        # -----------------------------------------
        # Revoke active sessions
        # -----------------------------------------

        revoked = UserSession.objects.filter(
            user=user,
            status=UserSession.Status.ACTIVE,
        ).update(
            status=UserSession.Status.REVOKED
        )

        # -----------------------------------------
        # Audit event
        # -----------------------------------------

        self.audit(
            event_type=AuditLog.Events.ACCOUNT_LOCKED,
            target=user,
            description=(
                "User account locked "
                "by administrator"
            ),
            metadata={
                "lock_type": "administrative",
                "reason": reason,
                "revoked_sessions": revoked,
            },
        )

        return Response(
            {
                "detail": (
                    f"User {user.email} has been "
                    "locked and logged out."
                )
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def unlock(self, request, public_id=None):

        user = get_object_or_404(
            User,
            public_id=public_id,
        )

        is_temp_locked = (
            user.locked_until is not None
        )

        if (
            not user.is_locked
            and not is_temp_locked
        ):

            return Response(
                {
                    "detail":
                    "User account is not locked."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------
        # Clear all lock state
        # -----------------------------------------

        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.last_failed_login_at = None
        user.locked_reason = ""

        user.save(update_fields=[
            "is_locked",
            "locked_until",
            "failed_login_attempts",
            "last_failed_login_at",
            "locked_reason",
        ])

        # -----------------------------------------
        # Audit event
        # -----------------------------------------

        self.audit(
            event_type=AuditLog.Events.ACCOUNT_UNLOCKED,
            target=user,
            description=(
                "User account unlocked "
                "by administrator"
            ),
            metadata={
                "unlock_type": "administrative",
            },
        )

        return Response(
            {
                "detail": (
                    f"User {user.email} "
                    "has been unlocked."
                )
            },
            status=status.HTTP_200_OK,
        )

class AdminResetUserPasswordView(AuditMixin, APIView):
    """
    Admin triggers a password reset for a user using public_id.
    Sends an email with a token-based reset link.
    """

    def post(self, request, user_public_id):
        serializer = AdminPasswordResetSerializer(
            data={"user_public_id": user_public_id}
        )
        serializer.is_valid(raise_exception=True)

        serializer.save(admin=request.user)

        return Response(
            {"detail": "Password reset link sent to user."},
            status=status.HTTP_200_OK,
        )
    
class AdminSetTemporaryPasswordView(AuditMixin, APIView):
    """
    Admin sets a temporary password for a user.
    User will be forced to change password at next login.
    """

    def post(self, request, user_public_id):
        serializer = AdminSetTemporaryPasswordSerializer(
            data={
                "user_public_id": user_public_id,
                "temporary_password": request.data.get("temporary_password"),
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(admin=request.user)

        return Response(
            {"detail": "Temporary password set successfully."},
            status=status.HTTP_200_OK,
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
    

class SiteNameChangeListAPIView(ListAPIView):
    queryset = SiteNameChangeHistory.objects.all().order_by("-changed_at")
    permission_classes = [IsAuthenticated]
    serializer_class = SiteNameChangeHistoryListSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = SiteNameChangeHistoryFilter
    pagination_class = FlexiblePagination

    ordering_fields = ["changed_at"]
    ordering = ["-changed_at"]

class SiteNameChangeDetailAPIView(RetrieveAPIView):
    queryset = SiteNameChangeHistory.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = SiteNameChangeHistorySerializer   

class SiteNameChangeAPIView( AuditMixin, NotificationMixin, GenericAPIView ):
    """
    POST-only endpoint to rename a Department, Location, or Room.

    Guarantees:
    - Rename + SiteNameChangeHistory + AuditLog are atomic
    - Reason is mandatory
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SiteNameChangeSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        

        site_type = data["site_type"]
        public_id = data["public_id"]
        new_name = data["new_name"]
        reason = data["reason"]

        model_map = {
            "department": Department,
            "location": Location,
            "room": Room,
        }

        model = model_map[site_type]

        try:
            obj = model.objects.select_for_update().get(public_id=public_id)
        except model.DoesNotExist:
            raise NotFound("Site not found.")

        old_name = obj.name

        if old_name == new_name:
            return Response(
                {"detail": "Name unchanged."},
                status=status.HTTP_200_OK,
            )

        # --------------------
        # Perform rename
        # --------------------

        obj.name = new_name
        obj.save(update_fields=["name"])

        # --------------------
        # Record site name-change history
        # --------------------

        SiteNameChangeHistory.objects.create(
            site_type=site_type,
            object_public_id=obj.public_id,
            old_name=old_name,
            new_name=new_name,
            user=request.user,
            user_email=request.user.email,
            reason=reason,
        )

        self.audit(
            event_type=AuditLog.Events.SITE_RENAMED,
            target=obj,
            description="Site name changed",
            metadata={
                "change_type": "site_rename",
                "old_name": old_name,
                "new_name": new_name,
                "reason": reason,
                "site_type": site_type,
            },
        )

        affected_users = get_users_affected_by_site(obj)

        for user in affected_users:
            self.notify(
                recipient=user,
                notif_type=AuditLog.Events.SITE_RENAMED,
                level=Notification.Level.INFO,
                title="Site renamed",
                message=(
                    f"{site_type.capitalize()} '{old_name}' "
                    f"has been renamed to '{new_name}'."
                ),
                entity=obj,
                actor=request.user,
            )

        return Response(
            {
                "status": "name updated",
                "site_type": site_type,
                "public_id": public_id,
                "old_name": old_name,
                "new_name": new_name,
            },
            status=status.HTTP_200_OK,
        )


class SiteRelocationAPIView(AuditMixin, NotificationMixin, GenericAPIView):
    """
    POST-only endpoint to relocate:
    - Location → Department
    - Room → Location
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SiteRelocationSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        site_type = data["site_type"]
        object_public_id = data["object_public_id"]
        target_site = data["target_site"]
        target_public_id = data["target_public_id"]
        reason = data["reason"]

        # --------------------
        # Relocate Location -> Department
        # --------------------

        if site_type == "location":
            try:
                obj = Location.objects.select_for_update().get(
                    public_id=object_public_id
                )
            except Location.DoesNotExist:
                raise NotFound("Location not found.")

            try:
                target = Department.objects.get(
                    public_id=target_public_id
                )
            except Department.DoesNotExist:
                raise NotFound("Target department not found.")

            from_parent = obj.department

            if from_parent == target:
                return Response(
                    {
                        "detail": (
                            "Location already under this department."
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            obj.department = target
            obj.save(update_fields=["department"])

        # --------------------
        # Relocate Room -> Location
        # --------------------

        elif site_type == "room":
            try:
                obj = Room.objects.select_for_update().get(
                    public_id=object_public_id
                )
            except Room.DoesNotExist:
                raise NotFound("Room not found.")

            try:
                target = Location.objects.get(
                    public_id=target_public_id
                )
            except Location.DoesNotExist:
                raise NotFound("Target location not found.")

            from_parent = obj.location

            if from_parent == target:
                return Response(
                    {
                        "detail": (
                            "Room already under this location."
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            obj.location = target
            obj.save(update_fields=["location"])

        else:
            raise ValidationError("Invalid site_type.")

        # --------------------
        # Record relocation history
        # --------------------

        SiteRelocationHistory.objects.create(
            site_type=site_type,
            object_public_id=obj.public_id,
            object_name=obj.name,

            from_parent_public_id=(
                from_parent.public_id if from_parent else ""
            ),
            from_parent_name=(
                from_parent.name if from_parent else ""
            ),

            to_parent_public_id=target.public_id,
            to_parent_name=target.name,

            user=request.user,
            user_email=request.user.email,
            reason=reason,
        )

        # --------------------
        # Audit log
        # --------------------

        self.audit(
            event_type=AuditLog.Events.SITE_RELOCATED,
            target=obj,
            description="Site relocated",
            metadata={
                "change_type": "site_relocation",
                "site_type": site_type,

                "from_parent_public_id": (
                    from_parent.public_id if from_parent else None
                ),
                "from_parent_name": (
                    from_parent.name if from_parent else None
                ),

                "to_parent_public_id": target.public_id,
                "to_parent_name": target.name,

                "reason": reason,
            },
        )

        affected_users = get_users_affected_by_site(obj)

        for user in affected_users:
            self.notify(
                recipient=user,
                notif_type=AuditLog.Events.SITE_RELOCATED,
                level=Notification.Level.CRITICAL,
                title="Site relocated",
                message=(
                    f"{site_type.capitalize()} '{obj.name}' was moved "
                    f"from '{from_parent.name if from_parent else 'N/A'}' "
                    f"to '{target.name}'."
                ),
                entity=obj,
                actor=request.user,
            )

        return Response(
            {
                "status": "relocation complete",
                "site_type": site_type,
                "object_public_id": obj.public_id,
                "from_parent": (
                    from_parent.public_id if from_parent else None
                ),
                "to_parent": target.public_id,
            },
            status=status.HTTP_200_OK,
        )



class AdminUpdateUserView(APIView):
    permission_classes = [AdminUpdateUserPermission]

    def patch(self, request, public_id):
        user = get_object_or_404(User, public_id=public_id)

        self.check_object_permissions(request, user)

        # Snapshot BEFORE
        before_data = {
            field: getattr(user, field)
            for field in AdminUserDemographicsSerializer.Meta.fields
        }

        serializer = AdminUserDemographicsSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Compute changes
        changes = {}
        for field, old_value in before_data.items():
            new_value = getattr(user, field)
            if old_value != new_value:
                changes[field] = {
                    "from": old_value,
                    "to": new_value,
                }

        # Audit log
        if changes:
            create_audit_log(
                request=request,
                event_type=AuditLog.Events.ADMIN_UPDATED_USER,
                description="Admin updated user demographic information",
                target=user,
                metadata={
                    "changes": changes,
                    "user_public_id": user.public_id,
                },
            )

        return Response(
            AdminUserDemographicsSerializer(user).data,
            status=status.HTTP_200_OK,
        )
    
class SessionActivityAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionJWTAuthentication]

    def post(self, request):
        auth = request.successful_authenticator
        session = getattr(auth, "session", None)

        if not session:
            return Response(
                {"detail": "No active session."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        now = timezone.now()

        # ------------------------------------------------
        # Ensure session is still active
        # ------------------------------------------------
        if session.status != UserSession.Status.ACTIVE:
            return Response(
                {"detail": "Session invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ------------------------------------------------
        # Absolute expiry enforcement
        # ------------------------------------------------
        if session.absolute_expires_at <= now:
            session.status = UserSession.Status.EXPIRED
            session.save(update_fields=["status"])

            return Response(
                {"detail": "Session expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ------------------------------------------------
        # Extend idle timeout using policy helper
        # ------------------------------------------------
        idle_timeout = get_session_idle_timeout()
        new_expiry = now + idle_timeout

        # Clamp to absolute lifetime
        if new_expiry > session.absolute_expires_at:
            new_expiry = session.absolute_expires_at

        # ------------------------------------------------
        # Prevent unnecessary DB writes
        # ------------------------------------------------
        if new_expiry - session.expires_at > timedelta(seconds=30):
            session.expires_at = new_expiry
            session.last_used_at = now
            session.save(update_fields=["expires_at", "last_used_at"])

        # ------------------------------------------------
        # Response for frontend timers
        # ------------------------------------------------
        return Response(
            {
                "ok": True,
                "idle_exp": int(session.expires_at.timestamp()),
                "abs_exp": int(session.absolute_expires_at.timestamp()),
            },
            status=status.HTTP_200_OK,
        )