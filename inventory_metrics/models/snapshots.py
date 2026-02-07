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
    department = models.ForeignKey( Department, on_delete=models.CASCADE, related_name="daily_snapshots", )
    snapshot_date = models.DateField(default=timezone.localdate, db_index=True)

    schema_version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=50, blank=True)

    total_users = models.PositiveIntegerField(default=0)
    total_admins = models.PositiveIntegerField( default=0,
        help_text=(
            "Users currently assigned to this department who hold an "
            "admin role scoped to this department, its locations/rooms, "
            "or globally (SITE_ADMIN)."
        ),
    )

    total_locations = models.PositiveIntegerField(default=0)
    total_rooms = models.PositiveIntegerField(default=0)

    total_equipment = models.PositiveIntegerField(default=0)

    equipment_ok = models.PositiveIntegerField( default=0, help_text="Equipment with status=OK in this department" )

    equipment_under_repair = models.PositiveIntegerField( default=0, help_text="Equipment currently under repair in this department" )

    equipment_damaged = models.PositiveIntegerField( default=0, help_text="Equipment marked as damaged in this department" )

    total_components = models.PositiveIntegerField(default=0)
    total_components_quantity = models.PositiveIntegerField(default=0)

    total_consumables = models.PositiveIntegerField(default=0)
    total_consumables_quantity = models.PositiveIntegerField(default=0)

    total_accessories = models.PositiveIntegerField(default=0)
    total_accessories_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["department", "snapshot_date"],
                name="uniq_department_snapshot_per_day",
            )
        ]
        indexes = [
            models.Index(fields=["snapshot_date", "department"]),
        ]

    def __str__(self):
        return f"Department {self.department.name} @ {self.snapshot_date}"
    

class DailyLocationSnapshot(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="daily_snapshots")
    snapshot_date = models.DateField(default=timezone.localdate, db_index=True)

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