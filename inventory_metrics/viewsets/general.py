import json
from django.shortcuts import get_object_or_404
import redis

from django.conf import settings
from django.http import Http404, JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import io
import json
from inventory_metrics.utils.excel_renderer import render_workbook
from inventory_metrics.utils.report_adapters.user_summary import user_summary_to_workbook_spec
from inventory_metrics.models.reports import ReportJob

from django.utils import timezone


redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)
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

        # still running
        if job.status in (
            ReportJob.Status.PENDING,
            ReportJob.Status.RUNNING,
        ):
            return JsonResponse(
                {"detail": "Report is still being generated."},
                status=202,
            )

        # failed
        if job.status == ReportJob.Status.FAILED:
            return JsonResponse(
                {
                    "detail": "Report generation failed.",
                    "error": job.error,
                },
                status=409,
            )

        redis_key = f"report:{job.public_id}"
        cached_payload = redis_client.get(redis_key)

        if not cached_payload:
            raise Http404("Report expired. Please regenerate.")

        payload = json.loads(cached_payload.decode("utf-8"))
        timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")

        if fmt == "json":
            response = JsonResponse(payload, safe=False)
            response["Content-Disposition"] = (
                f'attachment; filename="report-{job.public_id}-{timestamp}.json"'
            )
            return response

        # xlsx
        workbook_spec = user_summary_to_workbook_spec(payload)
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
            f'attachment; filename="report-{job.public_id}-{timestamp}.xlsx"'
        )
        return response