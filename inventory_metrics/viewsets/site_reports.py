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

        site_type = data['site_type']
        site_id = data['site_id']
        asset_types = data['asset_types']
        requested_file_name = data.get('file_name', 'site_assets')  # sanitized in serializer

        site_model = self.site_model_map[site_type]
        site_obj = get_object_or_404(site_model, public_id=site_id)

        excel_file = generate_site_asset_excel(site_obj, asset_types)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        final_file_name = f"{requested_file_name}_{timestamp}.xlsx"

        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{final_file_name}"'
        return response