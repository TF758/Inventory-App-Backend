from django.db import models

from db_inventory.models.site import Department, Location
from django.utils import timezone

class AdminMetricsSnapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    # Logical period
    period = models.CharField(
        max_length=20,
        choices=[("daily", "Daily")],
        default="daily",
        db_index=True,
    )

    schema_version = models.PositiveSmallIntegerField(default=1)

    # Source of truth
    data = models.JSONField()

    # Hot-path scalars (optional)
    users_count = models.IntegerField(null=True, blank=True)
    equipment_count = models.IntegerField(null=True, blank=True)

    source = models.CharField(max_length=50, default="celery")

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["period", "created_at"]),
        ]




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