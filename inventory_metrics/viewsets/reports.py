import json
from django.shortcuts import get_object_or_404
import redis
from rest_framework import viewsets
from django.conf import settings
from django.http import Http404, JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import json
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from db_inventory.pagination import FlexiblePagination
from inventory_metrics.filters import ReportJobFilter
from inventory_metrics.serializers.reports import ReportJobSerializer
from inventory_metrics.utils.report_adapters.site_reports import site_asset_to_workbook_spec, site_audit_log_to_workbook_spec
from inventory_metrics.utils.report_adapters.user_summary import user_summary_to_workbook_spec
from inventory_metrics.models.reports import ReportJob
from rest_framework import mixins, viewsets, permissions
import os

redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)


class DownloadReport(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id: str):

        job = get_object_or_404(
            ReportJob,
            public_id=public_id,
            user=request.user,
        )

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

        if not job.report_file:
            raise Http404("Report file not available.")

        file_path = settings.REPORTS_DIR / job.report_file

        if not file_path.exists():
            raise Http404("Report file not found.")
        
        print(job.report_file)

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=job.report_file,
        )
    
class MyReportJobViewSet( mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet, ):
    """
    Users can view and delete their own reports.
    Deleting a report removes the associated file.
    """

    serializer_class = ReportJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FlexiblePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReportJobFilter
    lookup_field = "public_id"

    def get_queryset(self):
        return (
            ReportJob.objects
            .filter(user=self.request.user)
            .order_by("-created_at")
        )

    def perform_destroy(self, instance):
        """
        Delete report file from disk when deleting the job.
        """

        if instance.report_file:
            file_path = os.path.join(settings.REPORTS_DIR, instance.report_file)

            if os.path.exists(file_path):
                os.remove(file_path)

        instance.delete()


class ReportJobAdminViewSet( mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet, ):
    serializer_class = ReportJobSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = FlexiblePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReportJobFilter
    lookup_field = "public_id"

    queryset = ReportJob.objects.select_related("user").order_by("-created_at")

    def perform_destroy(self, instance):

        if instance.report_file:
            file_path = os.path.join(settings.REPORTS_DIR, instance.report_file)

            if os.path.exists(file_path):
                os.remove(file_path)

        instance.delete()