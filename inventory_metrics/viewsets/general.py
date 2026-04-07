import json
from django.shortcuts import get_object_or_404
import redis

from django.conf import settings
from django.http import Http404, JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import io
import json
from inventory_metrics.utils.report_adapters.site_reports import site_asset_to_workbook_spec, site_audit_log_to_workbook_spec
from inventory_metrics.utils.excel_renderer import render_workbook
from inventory_metrics.utils.report_adapters.user_summary import user_summary_to_workbook_spec
from inventory_metrics.models.reports import ReportJob
from inventory_metrics.redis import redis_reports_client
from django.utils import timezone


redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)

REPORT_RENDERERS = {
    "user_summary": {
        "xlsx": user_summary_to_workbook_spec,
        "json": None,
    },
    "site_assets": {
        "xlsx": site_asset_to_workbook_spec,
        "json": None,
    },
    "site_audit_logs": {
        "xlsx": site_audit_log_to_workbook_spec,
        "json": None,
    },
     "asset_import": {
        "xlsx": None,
        "json": None,
    },
}

class DownloadReport(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id: str):

        job = get_object_or_404(
            ReportJob,
            public_id=public_id,
            user=request.user,
        )

        # -----------------------------
        # Job state handling
        # -----------------------------
        if job.status in (
            ReportJob.Status.PENDING,
            ReportJob.Status.RUNNING,
        ):
            return JsonResponse(
                {"detail": "Report is still being generated."},
                status=202,
            )

        if job.status == ReportJob.Status.FAILED:
            return JsonResponse(
                {
                    "detail": "Report generation failed.",
                    "error": job.error,
                },
                status=409,
            )

        # -----------------------------
        # Ensure file exists
        # -----------------------------
        if not job.report_file:
            raise Http404("Report file not available.")

        file_path = settings.REPORTS_DIR / job.report_file

        if not file_path.exists():
            raise Http404("Report file not found.")

        # -----------------------------
        # Stream file
        # -----------------------------
        with open(file_path, "rb") as f:
            response = HttpResponse(
                f.read(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )

        response["Content-Disposition"] = (
            f'attachment; filename="{job.report_file}"'
        )

        return response