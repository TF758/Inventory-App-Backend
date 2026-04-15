from rest_framework.permissions import IsAuthenticated

from db_inventory.models.assets import Accessory, Consumable, Equipment

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from reporting.api.serializers.asset_reports import AssetHistoryReportRequestSerializer
from reporting.models.reports import ReportJob
from reporting.tasks.reports import generate_report_task


class AssetHistoryReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AssetHistoryReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset_identifier = serializer.validated_data["asset_identifier"].strip()
        asset_type = serializer.validated_data["asset_type"]

        start_date = serializer.validated_data.get("start_date")
        end_date = serializer.validated_data.get("end_date")

        asset_exists = False

        if asset_type == "equipment":
            asset_exists = Equipment.objects.filter(
                public_id__iexact=asset_identifier
            ).exists()

        elif asset_type == "accessory":
            asset_exists = Accessory.objects.filter(
                public_id__iexact=asset_identifier
            ).exists()

        elif asset_type == "consumable":
            asset_exists = Consumable.objects.filter(
                public_id__iexact=asset_identifier
            ).exists()

        if not asset_exists:
            return Response(
                {"detail": "Invalid asset identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_HISTORY,
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