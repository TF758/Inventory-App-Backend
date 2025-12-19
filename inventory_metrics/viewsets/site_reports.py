from inventory_metrics.utils import generate_site_asset_excel
from inventory_metrics.serializers.site_reports import SiteAssetRequestSerializer
from rest_framework.views import APIView
from db_inventory.models import Department, Location, Room, AuditLog
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response


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
    API endpoint to generate Audit Log report for a given site
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
    def _to_report_row(self, log):
        local_time = log.created_at.astimezone()

        return {
            "date": local_time.strftime("%Y-%m-%d"),
            "time": local_time.strftime("%H:%M:%S"),
            "action": self.EVENT_LABELS.get(log.event_type, log.event_type),
            "performed_by": log.user_email or "System",
            "object_type": log.target_model,
            "object_name": log.target_name,
            "department": log.department_name,
            "location": log.location_name,
            "room": log.room_name,
            "ip_address": log.ip_address,
            "reference_id": log.public_id,
        }

    def post(self, request):
        data = request.data

        # -----------------------------
        # 1. Validate input
        # -----------------------------
        site_data = data.get('site')
        if not site_data:
            return Response(
                {"detail": "Missing 'site' object."},
                status=status.HTTP_400_BAD_REQUEST
            )

        site_type = site_data.get('siteType')
        site_id = site_data.get('siteId')

        if site_type not in self.site_model_map:
            return Response(
                {"detail": "Invalid siteType."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not site_id:
            return Response(
                {"detail": "Missing siteId."},
                status=status.HTTP_400_BAD_REQUEST
            )

        audit_period_days = int(data.get('audit_period_days', 30))
        if audit_period_days not in self.ALLOWED_PERIODS:
            return Response(
                {"detail": "Invalid audit_period_days. Allowed: 30, 60, 90, 120."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # 2. Ensure site exists
        # -----------------------------
        site_model = self.site_model_map[site_type]
        site = get_object_or_404(site_model, public_id=site_id)

        # -----------------------------
        # 3. Build time filter
        # -----------------------------
        start_date = timezone.now() - timedelta(days=audit_period_days)

        # -----------------------------
        # 4. Build queryset dynamically
        # -----------------------------
        site_filter_field = self.site_filter_field_map[site_type]

        audit_logs = (
            AuditLog.objects
            .filter(
                **{site_filter_field: site_id},
                created_at__gte=start_date
            )
            .select_related(
                'user', 'department', 'location', 'room'
            )
            .order_by('-created_at')
        )

        # -----------------------------
        # 5. Serialize response (simple)
        # -----------------------------
        rows = [self._to_report_row(log) for log in audit_logs]

        return Response(
            {
                "report": {
                    "site": {
                        "type": site_type,
                        "public_id": site_id,
                        "name": getattr(site, "name", None),
                    },
                    "period_days": audit_period_days,
                    "generated_at": timezone.now(),
                    "total_entries": audit_logs.count(),
                },
                "rows": rows,
            },
            status=status.HTTP_200_OK
        )