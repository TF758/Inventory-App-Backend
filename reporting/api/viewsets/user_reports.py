from rest_framework import status
from rest_framework.response import Response
from django.http import Http404, JsonResponse, HttpResponse
from django.conf import settings
from rest_framework.views import APIView
import io
from rest_framework.permissions import IsAuthenticated
import redis
from django.utils import timezone
from django.db.models import Q, Count
from db_inventory.models.audit import AuditLog
from inventory_metrics.utils.excel_renderer import estimate_excel_size_mb
from inventory_metrics.utils.resolve_audit_date_range import resolve_audit_date_range
from inventory_metrics.tasks.reports import generate_report_task
from inventory_metrics.models import ReportJob
from inventory_metrics.serializers.user_report import  UserAuditHistoryReportRequestSerializer, UserLoginHistoryReportRequestSerializer, UserSummaryReportRequestSerializer

redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)

from django.contrib.auth import get_user_model

User = get_user_model()


class UserSummaryReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserSummaryReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_identifier = serializer.validated_data["user"].strip()

        user_exists = User.objects.filter(
            Q(public_id__iexact=user_identifier) |
            Q(email__iexact=user_identifier)
        ).exists()

        if not user_exists:
            return Response(
                {"detail": "Invalid user identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
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

class UserAuditHistoryReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = UserAuditHistoryReportRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        user_identifier = serializer.validated_data["user"].strip()

        # -------------------------------------------------
        # Validate user existence
        # -------------------------------------------------

        user_exists = User.objects.filter(
            Q(public_id__iexact=user_identifier) |
            Q(email__iexact=user_identifier)
        ).exists()

        if not user_exists:
            return Response(
                {"detail": "Invalid user identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Create Report Job
        # -------------------------------------------------

        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.USER_AUDIT_HISTORY,
            params=serializer.validated_data,
        )

        # -------------------------------------------------
        # Queue Async Job
        # -------------------------------------------------

        generate_report_task.delay(job.id)

        return Response(
            {
                "report_id": job.public_id,
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )

class UserAuditHistoryPreview(APIView):
    permission_classes = [IsAuthenticated]

    PREVIEW_LIMIT = 100

    def post(self, request):

        serializer = UserAuditHistoryReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_identifier = serializer.validated_data["user"].strip()

        # -------------------------------------------------
        # Validate User Exists
        # -------------------------------------------------

        user = (
            User.objects.filter(public_id__iexact=user_identifier).first()
            or User.objects.filter(email__iexact=user_identifier).first()
        )

        if not user:
            return Response(
                {"detail": "Invalid user identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = serializer.validated_data

        start_date = params.get("start_date")
        end_date = params.get("end_date")
        relative_range = params.get("relative_range")

        # -------------------------------------------------
        # Resolve Date Range (reuse same logic as builder)
        # -------------------------------------------------

        start_date, end_date = resolve_audit_date_range(
            start_date=start_date,
            end_date=end_date,
            relative_range=relative_range,
        )

        # -------------------------------------------------
        # Base Query
        # -------------------------------------------------

        logs = AuditLog.objects.filter(user=user)

        if start_date:
            logs = logs.filter(created_at__gte=start_date)

        if end_date:
            logs = logs.filter(created_at__lte=end_date)

        # -------------------------------------------------
        # Aggregated Stats
        # -------------------------------------------------

        stats_qs = (
            logs.values("event_type")
            .annotate(count=Count("id"))
        )

        stats = {
            s["event_type"]: s["count"]
            for s in stats_qs
            if s["count"] > 0
        }

        # -------------------------------------------------
        # Preview Rows (latest 100)
        # -------------------------------------------------

        preview_qs = (
            logs
            .order_by("-created_at")
            .values(
                "created_at",
                "event_type",
                "description",
                "target_model",
                "target_id",
                "target_name",
                "ip_address",
            )[: self.PREVIEW_LIMIT]
        )

        preview = [
            {
                "timestamp": row["created_at"],
                "event_type": row["event_type"],
                "description": row["description"],
                "target_model": row["target_model"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "ip_address": row["ip_address"],
            }
            for row in preview_qs
        ]

        # -------------------------------------------------
        # Total Rows (useful for UI warnings)
        # -------------------------------------------------

        total_rows = logs.count()

        estimated_size_mb = estimate_excel_size_mb(total_rows)

        return Response(
            {
                "user": {
                    "public_id": user.public_id,
                    "email": user.email,
                    "full_name": user.get_full_name(),
                },
                "range": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "total_events": total_rows,
                "estimated_file_size_mb": estimated_size_mb,
                "stats": stats,
                "preview": preview,
            }
        )

class UserLoginHistoryReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = UserLoginHistoryReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Copy serializer data before modifying
        params = serializer.validated_data.copy()

        # Convert date objects to ISO strings for JSONField
        if params.get("start_date"):
            params["start_date"] = params["start_date"].isoformat()

        if params.get("end_date"):
            params["end_date"] = params["end_date"].isoformat()

        user_identifier = params["user"].strip()

        user_exists = User.objects.filter(
            Q(public_id__iexact=user_identifier) |
            Q(email__iexact=user_identifier)
        ).exists()

        if not user_exists:
            return Response(
                {"detail": "Invalid user identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.USER_LOGIN_HISTORY,
            params=params,
        )

        generate_report_task.delay(job.id)

        return Response(
            {
                "report_id": job.public_id,
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )