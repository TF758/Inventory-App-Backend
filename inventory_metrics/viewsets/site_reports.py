
from inventory_metrics.models.reports import ReportJob
from inventory_metrics.tasks import generate_site_asset_report_task, generate_site_audit_log_report_task
from inventory_metrics.serializers.site_reports import SiteAssetRequestSerializer, SiteAuditLogRequestSerializer
from rest_framework.views import APIView
from db_inventory.models import Department, Location, Room, AuditLog
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from openpyxl import Workbook
from openpyxl.styles import Font
from rest_framework.permissions import IsAuthenticated
import datetime



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

        generate_site_asset_report_task.delay(job.id)

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

        generate_site_audit_log_report_task.delay(job.id)

        return Response(
            {
                "report_id": job.public_id,
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )