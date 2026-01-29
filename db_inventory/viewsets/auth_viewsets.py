from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from db_inventory.models import UserSession, User, AuditLog, Department, Location, Room, SiteNameChangeHistory, SiteRelocationHistory
from db_inventory.serializers.auth import ChangePasswordSerializer, AdminPasswordResetSerializer, AuditLogLightSerializer, AdminUserDemographicsSerializer, SiteNameChangeHistoryListSerializer, SiteNameChangeHistorySerializer
from db_inventory.pagination import FlexiblePagination
from django_filters.rest_framework import DjangoFilterBackend
from db_inventory.filters import AuditLogFilter, SiteNameChangeHistoryFilter
from db_inventory.mixins import AuditMixin, ListDetailSerializerMixin, NotificationMixin, ScopeFilterMixin
from rest_framework.exceptions import ValidationError, NotFound
from django.db import transaction
from db_inventory.permissions.users import AdminUpdateUserPermission
from db_inventory.utils.audit import create_audit_log
from rest_framework.generics import ListAPIView, RetrieveAPIView
from db_inventory.models.security import Notification
from db_inventory.utils.viewset_helpers import get_users_affected_by_site

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

class SiteNameChangeAPIView(AuditMixin, NotificationMixin, APIView):
    """
    POST-only endpoint to rename a Department, Location, or Room.

    Guarantees:
    - Rename + SiteNameChangeHistory + AuditLog are atomic
    - Reason is mandatory
    """

    permission_classes = [IsAuthenticated]  

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        site_type = request.data.get("site_type")
        public_id = request.data.get("public_id")
        new_name = request.data.get("new_name")
        reason = request.data.get("reason")


        if not all([site_type, public_id, new_name, reason]):
            raise ValidationError(
                "site_type, public_id, new_name, and reason are required."
            )

        model_map = {
            "department": Department,
            "location": Location,
            "room": Room,
        }

        model = model_map.get(site_type)
        if not model:
            raise ValidationError("Invalid site_type. Must be department, location, or room.")

        try:
            obj = model.objects.select_for_update().get(public_id=public_id)
        except model.DoesNotExist:
            raise NotFound("Site not found.")

        old_name = obj.name
        if old_name == new_name:
            return Response({"detail": "Name unchanged."}, status=200)

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
            status=200,
        )


class SiteRelocationAPIView(AuditMixin,NotificationMixin, APIView):
    """
    POST-only endpoint to relocate:
    - Location → Department
    - Room → Location
    """

    permission_classes = [IsAuthenticated]  

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        site_type = request.data.get("site_type")
        object_public_id = request.data.get("object_public_id")
        target_site = request.data.get("target_site")
        target_public_id = request.data.get("target_public_id")
        reason = request.data.get("reason")

        if not all([site_type, object_public_id, target_site, target_public_id, reason]):
            raise ValidationError("All fields are required.")

        # --------------------
        # Validate relocation intent
        # --------------------

        if site_type == "location" and target_site != "department":
            raise ValidationError("Locations can only be moved under a department.")

        if site_type == "room" and target_site != "location":
            raise ValidationError("Rooms can only be moved under a location.")

        if site_type == "location":
            try:
                obj = Location.objects.select_for_update().get(
                    public_id=object_public_id
                )
            except Location.DoesNotExist:
                raise NotFound("Location not found.")

            try:
                target = Department.objects.get(public_id=target_public_id)
            except Department.DoesNotExist:
                raise NotFound("Target department not found.")

            from_parent = obj.department
            if from_parent == target:
                return Response({"detail": "Location already under this department."})

            obj.department = target
            obj.save(update_fields=["department"])

        elif site_type == "room":
            try:
                obj = Room.objects.select_for_update().get(
                    public_id=object_public_id
                )
            except Room.DoesNotExist:
                raise NotFound("Room not found.")

            try:
                target = Location.objects.get(public_id=target_public_id)
            except Location.DoesNotExist:
                raise NotFound("Target location not found.")

            from_parent = obj.location
            if from_parent == target:
                return Response({"detail": "Room already under this location."})

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

            from_parent_public_id=from_parent.public_id if from_parent else "",
            from_parent_name=from_parent.name if from_parent else "",

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

                    "from_parent_public_id": from_parent.public_id if from_parent else None,
                    "from_parent_name": from_parent.name if from_parent else None,

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
                "from_parent": from_parent.public_id if from_parent else None,
                "to_parent": target.public_id,
            },
            status=200,
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