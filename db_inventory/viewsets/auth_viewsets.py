from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from db_inventory.models import UserSession, User


class UserSessionViewSet(viewsets.GenericViewSet):
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
