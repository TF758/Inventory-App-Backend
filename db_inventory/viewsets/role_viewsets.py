from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from ..serializers.roles import ActiveRoleSerializer
from ..models import User, RoleAssignment

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

        try:
            role = RoleAssignment.objects.get(public_id=role_id)
        except RoleAssignment.DoesNotExist:
            raise NotFound(f"No role found with public_id: {role_id}")

        if role.user != request.user:
            raise PermissionDenied("You cannot activate a role not assigned to you.")

        # ✅ update the user, not the role
        request.user.active_role = role
        request.user.save(update_fields=["active_role"])

        return Response(
            {"active_role": role.public_id},
            status=status.HTTP_200_OK,
        )