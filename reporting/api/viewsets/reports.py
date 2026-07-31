from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from access.permissions.base import RequiresPermission
from core.pagination import FlexiblePagination
from reporting.api.serializers.reports import ReportJobSerializer
from reporting.filters import ReportJobFilter
from reporting.models.reports import ReportJob
from reporting.services.job_errors import public_job_error
from reporting.services.storage import (
    delete_report,
    open_report,
    report_download_name,
    report_exists,
)


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
            client_error = public_job_error(job)
            return JsonResponse(
                {
                    "detail": client_error,
                    "error": client_error,
                },
                status=409,
            )

        if not job.report_file:
            raise Http404("Report file not available.")

        if not report_exists(job.report_file):
            raise Http404("Report file not found.")

        return FileResponse(
            open_report(job.report_file),
            as_attachment=True,
            filename=report_download_name(job.report_file),
        )


class MyReportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Users can view and delete their own reports."""

    serializer_class = ReportJobSerializer
    permission_classes = [IsAuthenticated]
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
        delete_report(instance.report_file)
        instance.delete()


class ReportJobAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReportJobSerializer
    permission_classes = [RequiresPermission]
    required_permission = "reports.manage"
    pagination_class = FlexiblePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReportJobFilter
    lookup_field = "public_id"
    queryset = (
        ReportJob.objects
        .select_related("user")
        .order_by("-created_at")
    )

    def perform_destroy(self, instance):
        delete_report(instance.report_file)
        instance.delete()
