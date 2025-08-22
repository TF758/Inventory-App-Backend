from django.urls import path
from db_inventory.views import *

urlpatterns = [
    path('',location_list_create_view, name='locations'),
    path('<str:public_id>/', location_id_detail_view , name='location-detail'),

    path('<str:public_id>/rooms-full/', location_rooms_view, name='location-rooms'),
    # path('locations/<int:location_id>/rooms-dashboard/', location_rooms_dashboard_view, name='location-rooms-dashboard'),

    path('<str:public_id>/users-full/', locations_users_view, name='location-users'),
    # path('locations/<int:location_id>/users-dashboard/', locations_users_dashboard_view, name='location-users-dashboard'),

    path('<str:public_id>/equipment-full/', locations_equipment_view, name='location-equipment'),
    # path('locations/<int:location_id>/equipment-dashboard/', locations_equipment_dashboard_view, name='location-equipment-dashboard'),

    path('<str:public_id>/consumables-full/', location_consumables_view, name='location-consumables'),
    # path('locations/<int:location_id>/consumables-dashboard/', location_consumables_dashboard_view, name='location-consumables-dashboard'),

    path('<str:public_id>/accessories-full/', location_accessories_view, name='location-accessories'),
    # path('locations/<int:location_id>/accessories-dashboard/', location_accessories_dashboard_view, name='location-accessories-dashboard'),
]