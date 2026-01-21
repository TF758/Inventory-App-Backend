import uuid
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings
from db_inventory.models.base import PublicIDModel



class UserSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="sessions")
    refresh_token_hash = models.CharField(max_length=128, unique=True)
    previous_refresh_token_hash = models.CharField(max_length=128,null=True,blank=True,)
    status = models.CharField(max_length=10,choices=Status.choices,default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()               
    absolute_expires_at = models.DateTimeField()     
    last_used_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, null=True, blank=True)
    user_agent_hash = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["absolute_expires_at"]),
        ]

    def is_valid(self) -> bool:
        now = timezone.now()
        return (self.status == self.Status.ACTIVE and self.expires_at >= now)
    
    @staticmethod
    def hash_token(raw_token: str) -> str:
        """
        Hash a refresh token before storage or comparison.
        Never store raw tokens.
        """
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def __str__(self):
        return f"Session {self.id} ({self.status}) for {self.user}"

    @staticmethod
    def hash_user_agent(ua: str) -> str:
        return hashlib.sha256((ua or "").encode()).hexdigest()
    
class Notification(PublicIDModel):
   
    PUBLIC_ID_PREFIX = "NTF"

    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications", )
    type = models.CharField(max_length=100, help_text="Machine-readable notification type (e.g. asset_assigned)", )
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO, db_index=True, help_text="Severity level of the notification", )
    title = models.CharField( max_length=150, help_text="Short notification title", )
    message = models.CharField( max_length=255, help_text="Human-readable message shown to the user", )
    entity_type = models.CharField( max_length=100, null=True, blank=True, help_text="Model or domain type (e.g. asset)", )
    entity_id = models.CharField( max_length=100, null=True, blank=True, help_text="Public ID of the related object", )
    # State
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField( default=timezone.now, db_index=True, )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "level"]),
            models.Index(fields=["type"]),
            models.Index(fields=["created_at"]),
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