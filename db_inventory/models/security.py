import uuid
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings
from db_inventory.models.base import PublicIDModel
from django.core.cache import cache


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

class ScheduledTaskRun(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    task_name = models.CharField(max_length=100, db_index=True)
    run_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    message = models.TextField(blank=True)

    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    schema_version = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        duration = (
            f"{self.duration_ms}ms"
            if self.duration_ms is not None
            else "—"
        )
        return (
            f"{self.task_name} | "
            f"{self.get_status_display()} | "
            f"{self.run_at:%Y-%m-%d %H:%M} | "
            f"{duration}"
        )

class SecuritySettings(models.Model):
    """
    Global security policy configuration (singleton).
    """

    session_idle_minutes = models.PositiveIntegerField(default=30)
    session_absolute_hours = models.PositiveIntegerField(default=12)

    max_concurrent_sessions = models.PositiveIntegerField(default=5)

    lockout_attempts = models.PositiveIntegerField(default=5)
    lockout_duration_minutes = models.PositiveIntegerField(default=15)

    revoke_sessions_on_password_change = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    CACHE_KEY = "security_settings_singleton"

    CACHE_KEY = "security_settings_singleton"

    class Meta:
        verbose_name = "Security Settings"
        verbose_name_plural = "Security Settings"

    def save(self, *args, **kwargs):
        """
        Enforce singleton behavior.
        """
        self.pk = 1  # force primary key
        super().save(*args, **kwargs)

        # invalidate cache
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        """
        Prevent deletion of settings.
        """
        pass

    @classmethod
    def load(cls):
        """
        Load settings from cache or DB.
        """
        settings_obj = cache.get(cls.CACHE_KEY)

        if settings_obj:
            return settings_obj

        obj, created = cls.objects.get_or_create(pk=1)
        cache.set(cls.CACHE_KEY, obj, 300)

        return obj

    def __str__(self):
        return "System Security Settings"