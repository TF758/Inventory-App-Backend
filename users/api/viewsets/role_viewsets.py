from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from access.services.roles import RoleGovernanceService
from core.permissions.users import RoleAssignmentPermission
from access.hierachy import MANAGES_ALL
from users.services.active_roles import ActiveRoleService
from users.users_filters import RoleAssignmentFilter
from users.models.roles import RoleAssignment
from users.models.users import User
from core.permissions.helpers import ensure_permission
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from core.pagination import  FlexiblePagination
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Q
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from core.permissions.constants import ROLE_HIERARCHY
from users.api.serializers.roles import ActiveRoleSerializer, RoleReadSerializer, RoleWriteSerializer

from core.services.user_scope_cache import UserScopeCacheService

# --- Role Assignments CRUD ---
class RoleAssignmentViewSet(viewsets.ModelViewSet):
    """
    Handles listing, creating, retrieving, updating,
    and deleting RoleAssignment objects.

    Authorization model:
    - RoleAssignmentPermission checks permission capability.
    - RoleGovernanceService checks target role governance.
    - RoleGovernanceService checks target assignment scope.
    - RoleAssignment model validates final scope shape.
    """

    base_queryset = (
        RoleAssignment.objects
        .select_related(
            "user",
            "department",
            "location",
            "room",
        )
        .order_by(
            "-assigned_date",
            "-id",
        )
    )

    lookup_field = "public_id"

    permission_classes = [
        RoleAssignmentPermission,
    ]

    filter_backends = [
        DjangoFilterBackend,
    ]

    filterset_class = RoleAssignmentFilter
    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            return RoleWriteSerializer

        return RoleReadSerializer

    def get_queryset(self):
        user = self.request.user
        qs = self.base_queryset

        active_role = getattr(
            user,
            "active_role",
            None,
        )

        own_roles = qs.filter(
            user=user,
        )

        if not active_role:
            return own_roles

        if active_role.role == "SITE_ADMIN":
            return qs

        manageable_roles = RoleGovernanceService.get_manageable_roles(
            active_role,
        )

        if not manageable_roles:
            return own_roles

        scoped = qs

        if manageable_roles != MANAGES_ALL:
            scoped = scoped.filter(
                role__in=manageable_roles,
            )

        if active_role.department_id:
            scoped = scoped.filter(
                Q(
                    department_id=active_role.department_id,
                )
                | Q(
                    location__department_id=active_role.department_id,
                )
                | Q(
                    room__location__department_id=active_role.department_id,
                )
            )

        elif active_role.location_id:
            scoped = scoped.filter(
                Q(
                    location_id=active_role.location_id,
                )
                | Q(
                    room__location_id=active_role.location_id,
                )
            )

        elif active_role.room_id:
            scoped = scoped.filter(
                room_id=active_role.room_id,
            )

        else:
            return own_roles

        return (
            own_roles
            | scoped
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user

        active_role = getattr(
            user,
            "active_role",
            None,
        )

        data = serializer.validated_data

        if not RoleGovernanceService.can_assign(
            active_role,
            data["role"],
            room=data.get("room"),
            location=data.get("location"),
            department=data.get("department"),
        ):
            raise PermissionDenied(
                "You may not assign this role."
            )

        try:
            serializer.save(
                assigned_by=user,
            )

        except IntegrityError:
            raise ValidationError({
                "non_field_errors": [
                    "User already has this role in the specified scope."
                ]
            })

    def perform_update(self, serializer):
        user = self.request.user

        active_role = getattr(
            user,
            "active_role",
            None,
        )

        instance = serializer.instance
        data = serializer.validated_data

        target_role = data.get(
            "role",
            instance.role,
        )

        target_room = data.get(
            "room",
            instance.room,
        )

        target_location = data.get(
            "location",
            instance.location,
        )

        target_department = data.get(
            "department",
            instance.department,
        )

        if not RoleGovernanceService.can_update_assignment(
            active_role,
            instance,
            new_role=target_role,
            room=target_room,
            location=target_location,
            department=target_department,
        ):
            raise PermissionDenied(
                "You may not modify this role assignment."
            )

        try:
            updated_assignment = serializer.save(
                assigned_by=user,
            )

            UserScopeCacheService.invalidate_user_on_commit(
                updated_assignment.user.public_id,
                reason=(
                    "role_assignment_updated:"
                    f"{updated_assignment.public_id}"
                ),
            )

        except IntegrityError:
            raise ValidationError({
                "non_field_errors": [
                    "User already has this role in the specified scope."
                ]
            })

    def perform_destroy(self, instance):
        active_role = getattr(
            self.request.user,
            "active_role",
            None,
        )

        if not RoleGovernanceService.can_delete_assignment(
            active_role,
            instance,
        ):
            raise PermissionDenied(
                "You may not delete this role assignment."
            )

        affected_user_public_id = instance.user.public_id
        affected_role_public_id = instance.public_id

        instance.delete()

        UserScopeCacheService.invalidate_user_on_commit(
            affected_user_public_id,
            reason=(
                "role_assignment_deleted:"
                f"{affected_role_public_id}"
            ),
        )

# --- User Roles List (current user or any user by public_id) ---
class UserRoleList(ListAPIView):
    """
    Returns a list of roles for the current user or any other user given their public_id.
    """
    serializer_class = RoleReadSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_class = RoleAssignmentFilter

    def get_queryset(self):
        public_id = self.kwargs.get('public_id')
        if public_id:
            user = get_object_or_404(User, public_id=public_id)
        else:
            user = self.request.user
        return RoleAssignment.objects.filter(user=user).select_related(
            'department', 'location', 'room', 'assigned_by'
        )


# --- Active Role for Logged-in User ---
class ActiveRoleViewSet(viewsets.GenericViewSet):
    """
    Retrieve and update the currently active role for the logged-in user.
    """
    serializer_class = ActiveRoleSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        if not user.active_role:
            return Response({"active_role": None}, status=status.HTTP_200_OK)
        return Response({"active_role": user.active_role.public_id}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        role_id = kwargs.get("role_id")
        if not role_id:
            return Response(
                {"detail": "Role ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = ActiveRoleService.switch_active_role(
            user=request.user,
            role_public_id=role_id,
        )

        return Response(
            {"active_role": role.public_id},
            status=status.HTTP_200_OK,
        )