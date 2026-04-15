# reports/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from db_inventory.models.base import PublicIDModel

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

    class ReportType(models.TextChoices):
        USER_SUMMARY = "user_summary", "User Summary"
        SITE_ASSETS = "site_assets", "Site Assets"
        SITE_AUDIT_LOGS = "site_audit_logs", "Site Audit Logs"
        ASSET_IMPORT = "asset_import", "Asset Import"
        USER_AUDIT_HISTORY = "user_audit_history", "User Audit History"
        USER_LOGIN_HISTORY = "user_login_history", "User Login History"
        ASSET_HISTORY = "asset_history", "Asset History"

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

    class Meta:
        db_table = "inventory_metrics_reportjob"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "report_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.public_id} [{self.report_type} | {self.status}]"