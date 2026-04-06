from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class AssetType(models.TextChoices):
        EQUIPMENT = "equipment", "Equipment"
        ACCESSORY = "accessory", "Accessory"
        CONSUMABLE = "consumable", "Consumable"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="import_jobs",
    )
    asset_type = models.CharField(max_length=32, choices=AssetType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    source_file = models.FileField(upload_to="imports/source/")
    report_file = models.FileField(upload_to="imports/reports/", null=True, blank=True)

    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    skipped_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"ImportJob<{self.id}> {self.asset_type} {self.status}"