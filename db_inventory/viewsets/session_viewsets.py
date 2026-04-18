from django.db.models import Case, When, Value, IntegerField
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from db_inventory.models.security import UserSession
from db_inventory.serializers.sessions import UserSessionSerializer
from db_inventory.pagination import FlexiblePagination
from db_inventory.filters import UserSessionFilter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from users.models.users import User



class UserSessionViewSet(viewsets.GenericViewSet):

    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FlexiblePagination

    queryset = UserSession.objects.select_related("user")

    filter_backends = [DjangoFilterBackend]
    filterset_class = UserSessionFilter

    ordering = ["status", "-last_used_at"]

    # --------------------------------
    # List Sessions
    # --------------------------------
    def list(self, request):

        queryset = self.filter_queryset(self.get_queryset())

        queryset = queryset.annotate(
            status_priority=Case(
                When(status=UserSession.Status.ACTIVE, then=Value(0)),
                When(status=UserSession.Status.EXPIRED, then=Value(1)),
                When(status=UserSession.Status.REVOKED, then=Value(2)),
                output_field=IntegerField(),
            )
        ).order_by("status_priority", "-last_used_at")

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    # --------------------------------
    # Revoke a specific session
    # --------------------------------
    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):

        session = self.get_object()

        session.status = UserSession.Status.REVOKED
        session.save(update_fields=["status"])

        return Response(
            {"detail": "Session revoked."},
            status=status.HTTP_200_OK
        )

    # --------------------------------
    # Logout other devices
    # --------------------------------
    @action(detail=False, methods=["post"])
    def logout_others(self, request):

        session_id = request.auth.get("session_id")

        sessions = UserSession.objects.filter(
            user=request.user,
            status=UserSession.Status.ACTIVE
        ).exclude(id=session_id)

        revoked_count = sessions.update(status=UserSession.Status.REVOKED)

        return Response(
            {"revoked_sessions": revoked_count},
            status=status.HTTP_200_OK
        )

    # --------------------------------
    # Revoke sessions by IP
    # --------------------------------
    @action(detail=False, methods=["post"])
    def revoke_by_ip(self, request):

        ip_address = request.data.get("ip_address")

        if not ip_address:
            return Response(
                {"detail": "ip_address is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        sessions = UserSession.objects.filter(
            ip_address=ip_address,
            status=UserSession.Status.ACTIVE
        )

        revoked_count = sessions.update(status=UserSession.Status.REVOKED)

        return Response(
            {"revoked_sessions": revoked_count},
            status=status.HTTP_200_OK
        )

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