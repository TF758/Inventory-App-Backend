
from inventory_metrics.utils.viewset_helpers import generate_site_asset_excel
from inventory_metrics.serializers.site_reports import SiteAssetRequestSerializer
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

import datetime



class SiteAssetExcelReportAPIView(APIView):
    """
    API endpoint to generate Excel report for assets of a given site (department/location/room),
    allowing custom file name with timestamp.
    """

    site_model_map = {
        'department': Department,
        'location': Location,
        'room': Room
    }

    def post(self, request):
        serializer = SiteAssetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Extract site info from the nested 'site' object
        site_data = data['site']
        siteType = site_data['siteType']
        siteId = site_data['siteId']

        asset_types = data['asset_types']
        requested_file_name = data.get('file_name', 'site_assets')  # sanitized in serializer

        # Fetch the corresponding site object
        site_model = self.site_model_map[siteType]
        site_obj = get_object_or_404(site_model, public_id=siteId)

        # Generate Excel file
        excel_file = excel_file = generate_site_asset_excel(
                                site_type=siteType,
                                site_obj=site_obj,
                                asset_types=asset_types,
                                generated_by=request.user,
                            )
        # Add timestamp to filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        final_file_name = f"{requested_file_name}_{timestamp}.xlsx"

        # Return as downloadable response
        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{final_file_name}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response
    
class SiteAuditLogReportAPIView(APIView):
    """
    API endpoint to generate Audit Log Excel report for a given site
    (department / location / room) within a time period.
    """

    site_model_map = {
        'department': Department,
        'location': Location,
        'room': Room,
    }

    site_filter_field_map = {
        'department': 'department__public_id',
        'location': 'location__public_id',
        'room': 'room__public_id',
    }

    ALLOWED_PERIODS = {30, 60, 90, 120}

    EVENT_LABELS = {
        "login": "Login",
        "logout": "Logout",
        "model_created": "Created",
        "model_updated": "Updated",
        "model_deleted": "Deleted",
        "user_created": "User Created",
        "user_updated": "User Updated",
        "user_deleted": "User Deleted",
        "password_reset": "Password Reset",
        "role_assigned": "Role Assigned",
        "user_moved": "User Moved",
    }

    def post(self, request):
        data = request.data

        # -----------------------------
        # 1. Validate input
        # -----------------------------
        site_data = data.get("site")
        if not site_data:
            return Response({"detail": "Missing 'site' object."},
                            status=status.HTTP_400_BAD_REQUEST)

        site_type = site_data.get("siteType")
        site_id = site_data.get("siteId")

        if site_type not in self.site_model_map:
            return Response({"detail": "Invalid siteType."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not site_id:
            return Response({"detail": "Missing siteId."},
                            status=status.HTTP_400_BAD_REQUEST)

        audit_period_days = int(data.get("audit_period_days", 30))
        if audit_period_days not in self.ALLOWED_PERIODS:
            return Response(
                {"detail": "Invalid audit_period_days. Allowed: 30, 60, 90, 120."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # 2. Fetch data
        # -----------------------------
        site_model = self.site_model_map[site_type]
        site = get_object_or_404(site_model, public_id=site_id)

        start_date = timezone.now() - timedelta(days=audit_period_days)
        site_filter_field = self.site_filter_field_map[site_type]

        audit_logs = (
            AuditLog.objects
            .filter(**{site_filter_field: site_id},
                    created_at__gte=start_date)
            .select_related("user", "department", "location", "room")
            .order_by("-created_at")
        )

        # -----------------------------
        # 3. Build Excel workbook
        # -----------------------------
        wb = Workbook()
        ws = wb.active
        ws.title = "Audit Logs"

        headers = [
            "Date",
            "Time",
            "Action",
            "Performed By",
            "Affected Item Type",
            "Affected Item",
            "Department",
            "Location",
            "Room",
            "Source IP",
            "Audit Reference",
        ]

        ws.append(headers)

        # Bold header row
        for col in range(1, len(headers) + 1):
            ws.cell(row=1, column=col).font = Font(bold=True)

        for log in audit_logs:
            local_time = log.created_at.astimezone()

            ws.append([
                local_time.strftime("%Y-%m-%d"),
                local_time.strftime("%H:%M:%S"),

                self.EVENT_LABELS.get(log.event_type, log.event_type.replace("_", " ").title()),
                log.user_email or "System",

                log.target_model.replace("_", " ").title() if log.target_model else None,
                log.target_name,

                log.department_name,
                log.location_name,
                log.room_name,

                log.ip_address,
                log.public_id,
            ])

        # -----------------------------
        # 4. Return as Excel download
        # -----------------------------
        filename = (
            f"audit-log-{site_type}-{site.public_id}-"
            f"last-{audit_period_days}-days.xlsx"
        )

        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        wb.save(response)
        return response