from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from ..serializers.roles import *
from ..models import User, RoleAssignment
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from ..models import RoleAssignment, User
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from ..mixins import ScopeFilterMixin
from ..pagination import BasePagination, FlexiblePagination
from django_filters.rest_framework import DjangoFilterBackend
from ..filters import RoleAssignmentFilter
from ..permissions import RolePermission
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

        print("DEBUG --- user:", user.email)
        print("DEBUG --- is_superuser:", user.is_superuser)
        print("DEBUG --- active_role:", user.active_role)
        if user.active_role:
            print("DEBUG --- active_role.role:", user.active_role.role)
            print("DEBUG --- department:", user.active_role.department)
            print("DEBUG --- location:", user.active_role.location)
            print("DEBUG --- room:", user.active_role.room)

        # --- Superusers or site admins can see everything ---
        active = getattr(user, "active_role", None)
        if active and active.role == "SITE_ADMIN":
            return qs

        # --- Must have an active role ---
        active = getattr(user, "active_role", None)
        if not active:
            # No active role → only their own assignments
            return qs.filter(user=user)

        role = active.role

        # --- 3️⃣ Filter by scope ---
        if role == "DEPARTMENT_ADMIN":
            # See all roles within their department — direct + nested (location/room)
            return qs.filter(
                Q(department=active.department)
                | Q(location__department=active.department)
                | Q(room__location__department=active.department)
            )

        elif role == "LOCATION_ADMIN":
            # See roles within their location — direct + nested (room)
            return qs.filter(
                Q(location=active.location)
                | Q(room__location=active.location)
            )

        elif role == "ROOM_ADMIN":
            # See all roles in their room
            return qs.filter(room=active.room)

        elif role in ["ROOM_CLERK", "ROOM_VIEWER"]:
            # Can only see their own or others in the same room
            return qs.filter(Q(user=user) | Q(room=active.room))

        # Default fallback — self only
        return qs.filter(user=user)



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