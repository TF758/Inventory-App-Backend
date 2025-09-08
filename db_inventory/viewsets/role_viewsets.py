from rest_framework import viewsets, permissions, mixins
from ..serializers.roles import ActiveRoleSerializer
from ..models import User

class ActiveRoleViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    Retrieve and update the currently active role for the logged-in user.
    """
    serializer_class = ActiveRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
