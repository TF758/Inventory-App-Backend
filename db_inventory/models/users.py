from django.db import models
from django.utils import timezone

from users.models.users import User


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
