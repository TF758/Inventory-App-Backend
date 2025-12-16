from inventory_metrics.utils import generate_site_asset_excel
from inventory_metrics.serializers.site_reports import SiteAssetRequestSerializer
from rest_framework.views import APIView
from django.http import HttpResponse
from db_inventory.models import Department, Location, Room
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
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