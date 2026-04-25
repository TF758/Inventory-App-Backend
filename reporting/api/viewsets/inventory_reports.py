

from reporting.api.serializers.inventory_report import InventorySummaryReportRequestSerializer
from reporting.models.reports import ReportJob
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from reporting.tasks.reports import generate_report_task
from rest_framework.response import Response
from rest_framework import status

class InventorySummaryReport(APIView):
    """
    Queue Inventory Summary Report generation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InventorySummaryReportRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.INVENTORY_SUMMARY,
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