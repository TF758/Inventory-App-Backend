from django.contrib import admin

from inventory_metrics.models.reports import ReportJob
from inventory_metrics.models.snapshots import DailyDepartmentSnapshot
from inventory_metrics.models.metrics import DailyAuthMetrics, DailyReturnMetrics,DailySystemMetrics
from django.utils.html import format_html

@admin.register(ReportJob)
class ReportJobAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "user",
        "report_type",
        "status",
        "created_at",
        "finished_at",
        "download_link",
    )

    list_filter = (
        "report_type",
        "status",
        "created_at",
    )

    search_fields = (
        "public_id",
        "user__email",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "public_id",
        "created_at",
        "started_at",
        "finished_at",
        "download_link",
        "params",
        "error",
    )

    fieldsets = (
        ("Job Info", {
            "fields": (
                "public_id",
                "user",
                "report_type",
                "status",
            )
        }),
        ("Timing", {
            "fields": (
                "created_at",
                "started_at",
                "finished_at",
            )
        }),
        ("Report", {
            "fields": (
                "download_link",
                "params",
                "error",
            )
        }),
    )

    def download_link(self, obj):
        if not obj.report_file:
            return "-"

        return format_html(
            '<a href="/metrics/reports/{}/download/" target="_blank">Download</a>',
            obj.public_id,
        )

    download_link.short_description = "Report"

admin.site.register(DailyDepartmentSnapshot)

admin.site.register(DailyReturnMetrics)

admin.site.register(DailySystemMetrics)

admin.site.register(DailyAuthMetrics)