from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from reporting.api.serializers.site_reports import SiteAssetRequestSerializer, SiteAuditLogRequestSerializer
from reporting.models.reports import ReportJob
from reporting.tasks.reports import generate_report_task




class SiteAssetExcelReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SiteAssetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = ReportJob.objects.create(
            user=request.user,
            report_type="site_assets",
            params=serializer.validated_data,
        )

        generate_report_task.delay(job.id)

        return Response(
            {
                "report_id": job.public_id,
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )
    
class SiteAuditLogReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SiteAuditLogRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = ReportJob.objects.create(
            user=request.user,
            report_type="site_audit_logs",
            params=serializer.validated_data,
        )

        generate_report_task.delay(job.id)

        return Response(
            {
                "report_id": job.public_id,
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )