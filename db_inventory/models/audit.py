

from django.conf import settings
from db_inventory.models.base import PublicIDModel
from db_inventory.models.site import Department, Location,Room
from django.db import models
from db_inventory.models.users import User
from django.utils import timezone

\
class AuditLog(PublicIDModel):
    """
    audit log for security, and traceability.

    """

    PUBLIC_ID_PREFIX = "LOG"

    # --------------------
    # Actor (who did it)
    # --------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    # Snapshots (in case user is deleted or renamed)
    user_public_id = models.CharField(max_length=15, null=True, blank=True)
    user_email = models.EmailField(null=True, blank=True)

    # --------------------
    # Event
    # --------------------

    event_type = models.CharField(
        max_length=100,
        help_text="Machine-readable event identifier",
    )

    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description of the event",
    )

    metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional structured event data",
    )

    # --------------------
    # Target (what was affected)
    # --------------------

    target_model = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Model name of the affected object",
    )

    target_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Public ID of the affected object",
    )

    target_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Snapshot of object name at time of event",
    )

    # --------------------
    # Scope (site context)
    # --------------------

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    department_name = models.CharField(max_length=100, null=True, blank=True)

    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    location_name = models.CharField(max_length=255, null=True, blank=True)

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    room_name = models.CharField(max_length=255, null=True, blank=True)

    # --------------------
    # Request context
    # --------------------

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)

    # --------------------
    # Timestamp
    # --------------------

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["target_model", "target_id"]),
        ]

    # --------------------
    # Immutability enforcement
    # --------------------

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("AuditLog records are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditLog records cannot be deleted.")

    def __str__(self):
        actor = self.user_email or self.user_public_id or "System"
        return f"{self.event_type} by {actor} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    # --------------------
    # Common event constants
    # --------------------

    class Events:
        LOGIN = "login"
        LOGOUT = "logout"
        USER_CREATED = "user_created"
        USER_UPDATED = "user_updated"
        USER_DELETED = "user_deleted"

        PASSWORD_RESET_REQUESTED = "password_reset_requested"
        PASSWORD_RESET_COMPLETED = "password_reset_completed"

        ROLE_ASSIGNED = "role_assigned"
        ROLE_REVOKED = "role_revoked"

        MODEL_CREATED = "model_created"
        MODEL_UPDATED = "model_updated"
        MODEL_DELETED = "model_deleted"

        USER_MOVED = "user_moved"
        EXPORT_GENERATED = "export_generated"