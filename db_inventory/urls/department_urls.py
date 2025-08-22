from django.urls import path
from db_inventory.views import *


urlpatterns = [
    path('', department_list_create_view, name='departments'),
    path('<str:public_id>/', department_detail_view, name='department-detail'),

    path('<str:public_id>/users-full/', department_users_view, name='department-users'),
    path('<str:public_id>/users-light/', department_users_light_view, name='department-users-light'),

    path('<str:public_id>/locations-full/', department_locations_view, name='department-locations'),
    path('<str:public_id>/locations-light/', department_locations_light_view, name='department-locations-light'),

    path('<str:public_id>/equipment-full/', department_equipment_view, name='department-equipment'),
    path('<str:public_id>/equipment-light/', department_equipment_light_view, name='department-equipment-light'),

    path('<str:public_id>/consumables-full/', department_consumables_view, name='department-consumables'),
    path('<str:public_id>/consumables-light/', department_consumables_light_view, name='department-consumables-light'),

    path('<str:public_id>/accessories-full/', department_accessories_view, name='department-accessories'),
    path('<str:public_id>/accessories-light/', department_accessories_light_view, name='department-accessories-light'),

    path('<str:public_id>/components-full/', department_components_view, name='department-components'),
    path('<str:public_id>/components-light/', department_components_light_view, name='department-components-light'),
]
