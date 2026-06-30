from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response

from access.permissions.site_admin import IsActiveSiteAdmin
from access.serialziers import PermissionMatrixUpdateSerializer
from access.services.permissions import (
    PermissionMatrixService,
    PermissionMatrixSessionService,
)
from core.mixins import (
    AuditMixin,
    NotificationMixin,
)
from core.models.audit import AuditLog
from core.models.notifications import Notification


class PermissionMatrixView( AuditMixin, NotificationMixin, APIView ):

    permission_classes = [ IsActiveSiteAdmin ]

    def get( self, request):
        return Response(
            PermissionMatrixService.get_matrix()
        )

    def put( self, request ):

        serializer = PermissionMatrixUpdateSerializer( data=request.data)

        serializer.is_valid( raise_exception=True)
        
        current_session_id = None

        if getattr(request, "auth", None):
            current_session_id = request.auth.get(
                "session_id",
            )

        with transaction.atomic():
            matrix = PermissionMatrixService.update_matrix(
                serializer.validated_data,
            )

            changed = matrix["meta"]["changes"]["changed"]

            revocation = {
                "revoked_count": 0,
                "affected_users": [],
                "affected_user_ids": [],
            }

            if changed:
                revocation = (
                    PermissionMatrixSessionService
                    .revoke_after_matrix_update(
                        actor=request.user,
                        current_session_id=current_session_id,
                    )
                )

            self.audit(
                AuditLog.Events.PERMISSION_MATRIX_UPDATED,
                description=(
                    f"{request.user.email} updated the permission matrix."
                ),
                metadata={
                    "permission_changes": matrix["meta"]["changes"],
                    "sessions_revoked": revocation["revoked_count"],
                    "affected_users": len(
                        revocation["affected_user_ids"],
                    ),
                },
            )

            if changed:
                for user in revocation["affected_users"]:
                    self.notify(
                        recipient=user,
                        notif_type=Notification.NotificationType.SYSTEM,
                        level=Notification.Level.WARNING,
                        title="Session ended",
                        message=(
                            "Your session was ended because system "
                            "permissions were updated. Please sign in again."
                        ),
                        actor=request.user,
                        meta={
                            "reason": "permission_matrix_updated",
                            "actor_public_id": request.user.public_id,
                            "actor_email": request.user.email,
                        },
                    )

        matrix["meta"]["session_revocation"] = {
            "revoked": revocation["revoked_count"],
            "affected_users": len(
                revocation["affected_user_ids"],
            ),
        }

        return Response(
            matrix,
        )