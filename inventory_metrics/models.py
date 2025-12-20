from django.db import models
from db_inventory.models.site import Department, Location
from django.utils import timezone
# Create your models here.


class DailySystemMetrics(models.Model):
    date = models.DateField(unique=True)
    # User metrics
    total_users = models.IntegerField()
    active_users_last_24h = models.IntegerField()
    active_users_last_7d = models.IntegerField()
    new_users_last_24h = models.IntegerField()
    locked_users = models.IntegerField()
    # Session metrics
    total_sessions = models.IntegerField()
    active_sessions = models.IntegerField()
    revoked_sessions = models.IntegerField()
    expired_sessions_last_24h = models.IntegerField()
    unique_users_logged_in_last_24h = models.IntegerField()
    # Inventory metrics
    total_equipment = models.IntegerField()
    total_components = models.IntegerField()
    total_components_quantity = models.IntegerField()
    total_consumables = models.IntegerField()
    total_consumables_quantity = models.IntegerField()
    total_accessories = models.IntegerField()
    total_accessories_quantity = models.IntegerField()


    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ["-date"]
        verbose_name = "Daily System Metric"
        verbose_name_plural = "Daily System Metrics"


    def __str__(self):
        return f"DailySystemMetrics - {self.date.isoformat()}"
    
class DailySecurityMetrics(models.Model):
    date = models.DateField(unique=True)
    password_resets = models.IntegerField()
    active_password_resets = models.IntegerField()
    expired_password_resets = models.IntegerField()
    users_multiple_active_sessions = models.IntegerField()
    users_with_revoked_sessions = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = "Daily Security Metric"
        verbose_name_plural = "Daily Security Metrics"


    def __str__(self):
        return f"DailySecurityMetrics - {self.date.isoformat()}"
    

class DailyRoleMetrics(models.Model):
    date = models.DateField(db_index=True)
    role = models.CharField(max_length=64, db_index=True)
    total_users_with_role = models.IntegerField()
    total_users_active_with_role = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ("date", "role")
        verbose_name = "Daily Role Metric"
        verbose_name_plural = "Daily Role Metrics"


    def __str__(self):
        return f"{self.date} - {self.role}"

class DailyLoginMetrics(models.Model):
    date = models.DateField(unique=True, db_index=True)

    # Login events
    total_logins = models.IntegerField()
    unique_users_logged_in = models.IntegerField()
    failed_logins = models.IntegerField()
    lockouts = models.IntegerField()

    # Session-related
    active_sessions = models.IntegerField()
    revoked_sessions = models.IntegerField()
    expired_sessions = models.IntegerField()

    # Password recovery
    password_resets_started = models.IntegerField()
    password_resets_completed = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Daily Login Metric"
        verbose_name_plural = "Daily Login Metrics"

    def __str__(self):
        return f"DailyLoginMetrics - {self.date}"    

class DailyDepartmentSnapshot(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="daily_snapshots")
    snapshot_date = models.DateField(default=timezone.now, db_index=True)
    total_users = models.IntegerField()
    total_admins = models.IntegerField(default=0)
    total_locations = models.IntegerField()
    total_rooms = models.IntegerField()
    total_equipment = models.IntegerField()
    total_components = models.IntegerField()
    total_component_quantity = models.IntegerField()
    total_consumables = models.IntegerField()
    total_consumables_quantity = models.IntegerField()
    total_accessories = models.IntegerField()
    total_accessories_quantity = models.IntegerField()


    class Meta:
        unique_together = ("department", "snapshot_date")
        indexes = [models.Index(fields=["snapshot_date"])]


    def __str__(self):
        return f"Department {self.department.name} @ {self.snapshot_date}"
    

class DailyLocationSnapshot(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="daily_snapshots")
    snapshot_date = models.DateField(default=timezone.now, db_index=True)

    total_users = models.IntegerField()
    total_admins = models.IntegerField(default=0)
    total_rooms = models.IntegerField()
    total_equipment = models.IntegerField()
    total_components = models.IntegerField()
    total_component_quantity = models.IntegerField()
    total_consumables = models.IntegerField()
    total_consumables_quantity = models.IntegerField()
    total_accessories = models.IntegerField()
    total_accessories_quantity = models.IntegerField()


    class Meta:
        unique_together = ("location", "snapshot_date")
        indexes = [models.Index(fields=["snapshot_date"])]


    def __str__(self):
        return f"Location {self.location.name} @ {self.snapshot_date}"