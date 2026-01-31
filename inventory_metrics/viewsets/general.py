import json
from django.shortcuts import get_object_or_404
import redis

from django.conf import settings
from django.http import Http404, JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import io
import json
from inventory_metrics.utils.report_adapters.site_reports import site_asset_to_workbook_spec
from inventory_metrics.utils.excel_renderer import render_workbook
from inventory_metrics.utils.report_adapters.user_summary import user_summary_to_workbook_spec
from inventory_metrics.models.reports import ReportJob
from inventory_metrics.redis import redis_reports_client
from django.utils import timezone


redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)

REPORT_RENDERERS = {
    "user_summary": {
        "xlsx": user_summary_to_workbook_spec,
        "json": None,  # raw payload is returned
    },
    "site_assets": {
        "xlsx": site_asset_to_workbook_spec,
        "json": None,
    },
}


class DownloadReport(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id: str):
        fmt = request.GET.get("format", "xlsx").lower()

        if fmt not in {"json", "xlsx"}:
            return JsonResponse(
                {"detail": "Invalid format. Use ?format=json or ?format=xlsx."},
                status=400,
            )

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
        # Fetch cached payload
        # -----------------------------
        redis_key = f"report:{job.public_id}"
        cached_payload = redis_reports_client.get(redis_key)

        if not cached_payload:
            raise Http404("Report expired. Please regenerate.")

        payload = json.loads(cached_payload.decode("utf-8"))
        timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")

        report_type = job.params.get("report_type")
        renderer_cfg = REPORT_RENDERERS.get(report_type)

        if not renderer_cfg:
            return JsonResponse(
                {"detail": "Unsupported report type."},
                status=400,
            )

        # -----------------------------
        # JSON response
        # -----------------------------
        if fmt == "json":
            response = JsonResponse(payload, safe=False)
            response["Content-Disposition"] = (
                f'attachment; filename="report-{report_type}-{job.public_id}-{timestamp}.json"'
            )
            return response

        # -----------------------------
        # XLSX response
        # -----------------------------
        renderer = renderer_cfg.get("xlsx")
        if not renderer:
            return JsonResponse(
                {"detail": "XLSX format not supported for this report."},
                status=400,
            )

        workbook_spec = renderer(payload)
        wb = render_workbook(workbook_spec)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = (
            f'attachment; filename="report-{report_type}-{job.public_id}-{timestamp}.xlsx"'
        )
        return response