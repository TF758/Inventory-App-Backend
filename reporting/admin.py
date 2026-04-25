from django.contrib import admin
from django.utils.html import format_html
from reporting.models.reports import ReportJob

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
            '<a href="/reports/{}/download/" target="_blank">Download</a>',
            obj.public_id,
        )

    download_link.short_description = "Report"
