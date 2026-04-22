from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from data_import.tasks import run_asset_import_task
from data_import.utils import store_import_upload
from data_import.serializers import AssetImportRequestSerializer
from reporting.models.reports import ReportJob
import csv
from django.http import HttpResponse



class AssetImportCreateView(APIView):
    permission_classes = [IsAuthenticated]

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

        run_asset_import_task.delay(job.id)

        return Response(
            {
                "job_id": job.public_id,
                "status": job.status,
                "message": "Import started.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

class AssetImportStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_object_or_404(
            ReportJob,
            public_id=job_id,
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
        )

        payload = job.result_payload or {}

        return Response({
            "job_id": job.public_id,
            "status": job.status,
            "summary": payload.get("summary"),
            "issues": payload.get("issues", []),
            "error": job.error,
            "fatal_error": payload.get("fatal_error"),
        })

class AssetImportErrorDownloadView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):

        job = get_object_or_404(
            ReportJob,
            public_id=job_id,
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
        )

        if job.status in ["COMPLETED", "FAILED"]:
            return Response(
                {"detail": "Job already finished."},
                status=400,
            )

        job.status = "CANCELLED"
        job.save()

        return Response({"status": "cancelled"})