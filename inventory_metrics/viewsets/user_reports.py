from rest_framework import status
from rest_framework.response import Response
from django.http import Http404, JsonResponse, HttpResponse
from django.conf import settings
from rest_framework.views import APIView
import io
from rest_framework.permissions import IsAuthenticated
import redis
from django.utils import timezone
import json

from urllib3 import request
from inventory_metrics.tasks.reports import generate_report_task
from inventory_metrics.models import ReportJob
from inventory_metrics.serializers.user_report import UserSummaryReportSerializer, UserSummaryReportRequestSerializer

redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)



class UserSummaryReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserSummaryReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = ReportJob.objects.create(
            user=request.user,
            report_type="user_summary",
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