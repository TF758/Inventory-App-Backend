from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from data_import.tasks import run_asset_import_task
from data_import.utils import store_import_upload
from data_import.serializers import AssetImportRequestSerializer
from inventory_metrics.models.reports import ReportJob



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
            params={
                "job_type": "asset_import",
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

class ImportErrorReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):

        job = ReportJob.objects.get(public_id=job_id, user=request.user)

        if not job.error_report_csv:
            return Response(
                {"detail": "No error report available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = HttpResponse(
            job.error_report_csv,
            content_type="text/csv",
        )

        response["Content-Disposition"] = (
            f'attachment; filename="import_errors_{job.public_id}.csv"'
        )

        return response