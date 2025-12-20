from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from db_inventory.serializers.roles import *
from db_inventory.models.users import User
from db_inventory.models.roles import RoleAssignment
from db_inventory.permissions.helpers import ensure_permission
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from db_inventory.pagination import  FlexiblePagination
from django_filters.rest_framework import DjangoFilterBackend
from db_inventory.filters import RoleAssignmentFilter
from db_inventory.permissions import RolePermission
from django.db.models import Q

# --- Role Assignments CRUD ---
class RoleAssignmentViewSet(viewsets.ModelViewSet):
    """
    Handles listing, creating, retrieving, updating, and deleting RoleAssignment objects.
    """
    base_queryset = (
        RoleAssignment.objects
        .select_related("user", "department", "location", "room")
        .order_by("-assigned_date", "-id")
    )
    lookup_field = "public_id"
    permission_classes = [RolePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RoleAssignmentFilter
    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoleWriteSerializer
        return RoleReadSerializer

    def get_queryset(self):
        user = self.request.user
        qs = self.base_queryset

        active = getattr(user, "active_role", None)
        if active and active.role == "SITE_ADMIN":
            return qs

        if not active:
            return qs.filter(user=user)

        role = active.role

        if role == "DEPARTMENT_ADMIN":
            return qs.filter(
                Q(department=active.department)
                | Q(location__department=active.department)
                | Q(room__location__department=active.department)
            )
        elif role == "LOCATION_ADMIN":
            return qs.filter(
                Q(location=active.location)
                | Q(room__location=active.location)
            )
        elif role == "ROOM_ADMIN":
            return qs.filter(room=active.room)
        elif role in ["ROOM_CLERK", "ROOM_VIEWER"]:
            return qs.filter(Q(user=user) | Q(room=active.room))

        return qs.filter(user=user)

    # ------------------------------
    # Enforce permission before serializer.save()
    # ------------------------------
    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data

        # Pre-check permissions before saving
        ensure_permission(
            user,
            data['role'],
            data.get('room'),
            data.get('location'),
            data.get('department')
        )

        serializer.save(assigned_by=user)

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data

        ensure_permission(
            user,
            data.get('role', serializer.instance.role),
            data.get('room', serializer.instance.room),
            data.get('location', serializer.instance.location),
            data.get('department', serializer.instance.department)
        )

        serializer.save(assigned_by=user)


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
            return Response({"detail": "Role ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        role = get_object_or_404(RoleAssignment, public_id=role_id)
        if role.user != request.user:
            raise PermissionDenied("Cannot activate a role not assigned to you.")

        request.user.active_role = role
        request.user.save(update_fields=["active_role"])
        return Response({"active_role": role.public_id})