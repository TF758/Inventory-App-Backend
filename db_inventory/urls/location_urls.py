from django.urls import path
from db_inventory.views import *

urlpatterns = [
    path('',location_list_create_view, name='locations'),
     path('list/',location_list_view, name='locations-list'),
    path('<str:public_id>/', location_id_detail_view , name='location-detail'),

    path('<str:public_id>/rooms-full/', location_rooms_view, name='location-rooms'),
    path('<str:public_id>/rooms-light/', location_rooms_light_view, name='location-rooms-light'),

    path('<str:public_id>/users-full/', locations_users_view, name='location-users'),
    path('<str:public_id>/users-light/', locations_users_light_view, name='location-users-light'),

    path('<str:public_id>/equipment-full/', locations_equipment_view, name='location-equipment'),
    path('<str:public_id>/equipment-light/', locations_equipment_light_view, name='location-equipment-light'),

    path('<str:public_id>/consumables-full/', location_consumables_view, name='location-consumables'),
    path('<str:public_id>/consumables-light/', location_consumables_light_view, name='location-consumables-light'),
    
    path('<str:public_id>/accessories-full/', location_accessories_view, name='location-accessories'),
    path('<str:public_id>/accessories-light/', location_accessories_light_view, name='location-accessories-light'),

    path('<str:public_id>/components-full/', location_components_view, name='location-components'),
    path('<str:public_id>/components-light/', location_components_light_view, name='location-components-light'),

    path('<str:public_id>/roles/', location_roles_view, name='location-roles'),
]