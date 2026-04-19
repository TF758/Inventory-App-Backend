
from django.db import models


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
