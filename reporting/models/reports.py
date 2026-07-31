# reports/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import PublicIDModel

class ReportJob(PublicIDModel):
    """
    Async report / job record.
    """

    PUBLIC_ID_PREFIX = "RPT"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class ReportType(models.TextChoices):
        USER_SUMMARY = "user_summary", "User Summary"
        SITE_ASSETS = "site_assets", "Site Assets"
        SITE_AUDIT_LOGS = "site_audit_logs", "Site Audit Logs"
        ASSET_IMPORT = "asset_import", "Asset Import"
        USER_AUDIT_HISTORY = "user_audit_history", "User Audit History"
        USER_LOGIN_HISTORY = "user_login_history", "User Login History"
        ASSET_HISTORY = "asset_history", "Asset History"
        INVENTORY_SUMMARY = "inventory_summary", "Inventory Summary"

    user = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="report_jobs", )

    report_type = models.CharField( max_length=40, choices=ReportType.choices, db_index=True, )

    status = models.CharField( max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True, )

    params = models.JSONField()

    error = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    report_file = models.CharField(max_length=500, blank=True)

    result_payload = models.JSONField(null=True, blank=True)

    notification_sent = models.BooleanField(default=False)

    # Celery execution lease. The task id identifies the worker delivery that
    # currently owns this job; heartbeat_at lets the recovery task distinguish
    # active work from a worker that disappeared.
    task_id = models.CharField(max_length=255, blank=True, db_index=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    heartbeat_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "report_type"]),
            models.Index(fields=["created_at"]),
            models.Index(
                fields=["status", "heartbeat_at"],
                name="report_job_status_hb_idx",
            ),
        ]

    def __str__(self):
        return f"{self.public_id} [{self.report_type} | {self.status}]"