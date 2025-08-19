from django.urls import path
from . import api_views
from  db_inventory.viewsets import *


urlpatterns = [

    path('users/', user_list_create_view, name='users'),
    path('users/<int:id>/',user_id_detail_view, name='user-detail'),

    path('departments/', department_list_create_view, name='departments'),
    path('department/<int:id>/', department_id_detail_view, name='department-detail'),
    path('department/<int:department_id>/users/', department_users_view, name='department-users'),
    path('department/<int:department_id>/locations/', department_locations_view, name='department-locations'),
    path('department/<int:department_id>/equipment/', department_equipment_view, name='department-equipment'),
    path('department/<int:department_id>/consumables/', department_consumables_view, name='department-consumables'),
    path('department/<int:department_id>/accessories/', department_accessories_view, name='department-accessories'),
    path('department/<int:department_id>/components/', department_users_view, name='department-components'),


    path('locations/',location_list_create_view, name='locations'),
    path('locations/<int:id>/', location_id_detail_view , name='location-detail'),
    path('locations/<int:location_id>/rooms/', location_rooms_view , name='location-rooms'),
    path('locations/<int:location_id>/users/', locations_users_view , name='location-users'),
    path('locations/<int:location_id>/equipment/', locations_equipment_view , name='location-equipment'),
    path('locations/<int:location_id>/consumables/', location_consumables_view , name='location-consumables'),
    path('locations/<int:location_id>/accessories/', location_accessories_view , name='location-accessories'),

    
    path('rooms/',room_list_create_view, name='rooms'),
    path('rooms/<int:id>/', room_id_detail_view , name='room-detail'),
    path('rooms/<int:room_id>/users/', room_users_view , name='room-users'),
    path('rooms/<int:room_id>/equipment/', room_equipment_view , name='room-equipment'),
    path('rooms/<int:room_id>/consumables/', room_consumables_view , name='room-consumables'),
    path('rooms/<int:room_id>/accessories/', room_accessories_view , name='room-accessories'),
    path('rooms/<int:room_id>/components/', room_components_view , name='room-components'),



    path('equipments/', equipment_list_create_view, name='equipments'),
    path('equipment/<int:id>/', equipment_id_detail_view, name='equipment-detail'),

    path('components/', component_list_create_view, name='components'), 
    path('components/<int:id>/', component_id_detail_view, name='component-detail'),


    path('accessories/', accessory_list_create_view, name='accessories'),
    path('accessories/<int:id>/', accessory_id_detail_view, name='accessory-detail'),

    path('consumables/', consumable_list_create_view, name="consumables"),
    path('consumables/<int:id>/', consumable_id_detail_view, name='consumable-detail'),

]