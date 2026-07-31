from celery import current_app
import logging
from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from data_import.utils import delete_import_upload, store_import_upload
from data_import.serializers import AssetImportRequestSerializer
from core.mixins import AuditMixin, NotificationMixin
from core.models.audit import AuditLog
from access.permissions.base import RequiresPermission
from reporting.models.reports import ReportJob
from reporting.services.job_errors import public_job_error
from reporting.services.job_dispatch import enqueue_report_job
import csv
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class AssetImportCreateView(NotificationMixin, AuditMixin, APIView):
    permission_classes = [ RequiresPermission]

    required_permission = ( "assets.import" )

    def post(self, request):
        serializer = AssetImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        asset_type = serializer.validated_data["asset_type"]

        stored_file_name = store_import_upload(uploaded_file)

        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": asset_type,
                "stored_file_name": stored_file_name,
                "original_file_name": uploaded_file.name,
            },
        )

        enqueue_report_job(job.id)

        self.notify(
            recipient=request.user,
            notif_type="asset_import_started",
            title="Import started",
            message="Your import is being processed. A report will be available shortly.",
            entity=job,
            meta={
                "job_id": job.public_id,
                "asset_type": asset_type,
            },
        )

        self.audit(
            event_type=AuditLog.Events.ASSET_IMPORT_STARTED,
            target=job,
            description=f"{asset_type.title()} import started",
            metadata={
                "job_id": job.public_id,
                "asset_type": asset_type,
                "file_name": uploaded_file.name,
            },
        )

        return Response(
            {
                "job_id": job.public_id,
                "status": job.status,
                "message": "Import started.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

class AssetImportStatusView(APIView):

    permission_classes = [ RequiresPermission ]

    required_permission = ( "assets.import" )

    def get(self, request, job_id):
        job = get_object_or_404(
            ReportJob,
            public_id=job_id,
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
        )

        payload = job.result_payload or {}

        client_error = public_job_error(job) or None

        return Response({
            "job_id": job.public_id,
            "status": job.status,
            "summary": payload.get("summary"),
            "issues": payload.get("issues", []),
            "error": client_error,
            "fatal_error": client_error,
        })

class AssetImportErrorDownloadView(APIView):
    permission_classes = [ RequiresPermission ]

    required_permission = ( "assets.import" )


    def get(self, request, job_id):

        job = get_object_or_404(
            ReportJob,
            public_id=job_id,
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
        )

        payload = job.result_payload or {}
        issues = payload.get("issues", [])

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="import_errors_{job.public_id}.csv"'

        writer = csv.writer(response)
        writer.writerow(["row_number", "status", "reason", "row_data"])

        for issue in issues:
            writer.writerow([
                issue["row_number"],
                issue["status"],
                issue["reason"],
                issue["row_data"],
            ])

        return response

class AssetImportCancelView(APIView):
    permission_classes = [ RequiresPermission ]

    required_permission = ( "assets.import" )


    def post(self, request, job_id):

        job = get_object_or_404(
            ReportJob,
            public_id=job_id,
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
        )

        terminal_statuses = {
            ReportJob.Status.DONE,
            ReportJob.Status.FAILED,
            ReportJob.Status.CANCELLED,
        }

        if job.status in terminal_statuses:
            return Response(
                {"detail": "Job already finished."},
                status=status.HTTP_409_CONFLICT,
            )

        active_task_id = job.task_id
        updated = ReportJob.objects.filter(
            pk=job.pk,
            status__in=[
                ReportJob.Status.PENDING,
                ReportJob.Status.RUNNING,
            ],
        ).update(
            status=ReportJob.Status.CANCELLED,
            finished_at=timezone.now(),
            heartbeat_at=None,
            task_id="",
        )

        if not updated:
            return Response(
                {"detail": "Job could not be cancelled."},
                status=status.HTTP_409_CONFLICT,
            )

        if active_task_id:
            try:
                current_app.control.revoke(
                    active_task_id,
                    terminate=False,
                )
            except Exception:
                logger.exception(
                    "asset_import_task_revoke_failed",
                    extra={"job_id": job.id},
                )

        try:
            delete_import_upload(
                (job.params or {}).get("stored_file_name", "")
            )
        except Exception:
            logger.exception(
                "asset_import_cancel_upload_cleanup_failed",
                extra={"job_id": job.id},
            )

        return Response({"status": ReportJob.Status.CANCELLED})