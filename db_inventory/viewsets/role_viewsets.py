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

class RoleAssignmentViewSet(ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing RoleAssignment objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for RoleAssignment objects."""

    queryset = RoleAssignment.objects.all().order_by("-assigned_date", "-id")
    lookup_field = 'public_id'

    pagination_class = FlexiblePagination
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoleWriteSerializer
        return RoleReadSerializer


class ActiveRoleViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """
    Retrieve and update the currently active role for the logged-in user.
    """
    serializer_class = ActiveRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """
        GET /roles/me/active-role/
        Returns the current active role (public_id) for the logged-in user.
        """
        user = request.user
        if not user.active_role:
            return Response({"active_role": None}, status=status.HTTP_200_OK)

        return Response(
            {"active_role": user.active_role.public_id},
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        """
        PUT /roles/me/active-role/<public_id>/
        Sets the given role assignment (by public_id) as the user's active role.
        """
        role_id = kwargs.get("role_id")
        if not role_id:
            raise NotFound("Role ID is required.")

        role = get_object_or_404(RoleAssignment, public_id=role_id)

        if role.user != request.user:
            raise PermissionDenied("Cannot activate a role not assigned to you.")

        request.user.active_role = role
        request.user.save(update_fields=["active_role"])
        return Response({"active_role": role.public_id})
        

class MyRoleList(ListAPIView):
    serializer_class = RoleReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.role_assignments.select_related(
            'department', 'location', 'room', 'assigned_by'
        )

  
class RoleDetailView(viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.all()
    permission_classes = [IsAuthenticated]

    lookup_field = 'public_id'

    def get_queryset(self):
        # optimize related objects to avoid N+1 queries
        return RoleAssignment.objects.select_related(
            'user', 'department', 'location', 'room', 'assigned_by'
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoleWriteSerializer
        return RoleReadSerializer


class UserRoleListView(ListAPIView):

    """Returns a list of all the roles for a given user using thier public id"""
    queryset = RoleAssignment.objects.all().order_by('role')
    lookup_field = 'public_id'
    serializer_class = RoleReadSerializer


    def get_queryset(self):
        public_id = self.kwargs.get('public_id')
        try:
            user = User.objects.get(public_id=public_id)
        except User.DoesNotExist:
            return RoleAssignment.objects.none()

        return RoleAssignment.objects.filter(user=user).select_related(
            'department', 'location', 'room', 'assigned_by'
        )

class UserRoleCreateView(CreateAPIView):
    serializer_class = RoleWriteSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        public_id = self.kwargs.get("public_id")
        user = get_object_or_404(User, public_id=public_id)
        serializer.save(user=user, assigned_by=self.request.user)