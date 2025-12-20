import uuid
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings


class UserSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    refresh_token_hash = models.CharField(max_length=128, unique=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
        ]

    def mark_revoked(self):
        """Revoke this session immediately."""
        self.status = self.Status.REVOKED
        self.save(update_fields=["status"])

    def mark_expired(self):
        """Mark the session as expired."""
        self.status = self.Status.EXPIRED
        self.save(update_fields=["status"])

    def is_valid(self) -> bool:
        """
        A session is valid if:
        - status is ACTIVE
        - expiry time has not passed
        """
        return (
            self.status == self.Status.ACTIVE
            and self.expires_at >= timezone.now()
        )
    
    @staticmethod
    def hash_token(raw_token: str) -> str:
        """
        Hash a refresh token before storage or comparison.
        Never store raw tokens.
        """
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def __str__(self):
        return f"Session {self.id} ({self.status}) for {self.user}"
