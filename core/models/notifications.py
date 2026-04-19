from django.db import models
from django.utils import timezone
from django.conf import settings
from core.models.base import PublicIDModel

  
class Notification(PublicIDModel):
    PUBLIC_ID_PREFIX = "NTF"
    PUBLIC_ID_PERMANENT = False

    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class NotificationType(models.TextChoices):
        REPORT_READY = "report_ready", "Report Ready"
        ASSET_ASSIGNED = "asset_assigned", "Asset Assigned"
        PASSWORD_RESET = "password_reset", "Password Reset"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications", )

    type = models.CharField( max_length=100, choices=NotificationType.choices, db_index=True, )

    level = models.CharField( max_length=20, choices=Level.choices, default=Level.INFO, db_index=True, )
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=255)

    entity_type = models.CharField(max_length=100, null=True, blank=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True)

    meta = models.JSONField(null=True, blank=True) 

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    class Meta:
        ordering = ["-created_at",  "-id"]
        indexes = [
        models.Index(fields=["recipient", "is_deleted", "-created_at"]),
        models.Index(fields=["recipient", "is_read"]),
        models.Index(fields=["recipient", "level"]),
        models.Index(fields=["type"]),
    ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return (
            f"{self.type} [{self.level}] → "
            f"{self.recipient} ({'read' if self.is_read else 'unread'})"
        )

