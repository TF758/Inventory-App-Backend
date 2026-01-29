# reports/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from db_inventory.models.base import PublicIDModel




class ReportJob(PublicIDModel):
    """
    Ephemeral async report job.
    Payload lives in Redis, not DB.
    """

    PUBLIC_ID_PREFIX = "RPT"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"

    user = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="report_jobs", )

    status = models.CharField( max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True, )

    # Input parameters used to build the report
    params = models.JSONField()

    error = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    notification_sent = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.public_id} [{self.status}]"