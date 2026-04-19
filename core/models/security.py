
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from users.models.users import User


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


class PasswordResetEvent(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="password_reset_events")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_password_resets")
    token = models.CharField(max_length=255, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (
            self.is_active
            and self.used_at is None
            and self.expires_at >= timezone.now()
        )

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
