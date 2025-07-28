from django.urls import path
from . import api_views
from  db_inventory.viewsets import *


urlpatterns = [

    path('users/', user_list_create_view, name='users'),
    path('users/<int:id>/',user_id_detail_view, name='user-detail'),

    path('departments/', department_list_create_view, name='departments'),
    path('departments/<int:id>/', department_id_detail_view, name='department-detail'),


    path('locations/',location_list_create_view, name='locations'),
    path('locations/<int:id>/', location_id_detail_view , name='location-detail'),


    path('equipments/', equipment_list_create_view, name='equipments'),
    path('equipment/<int:id>/', equipment_id_detail_view, name='equipment-detail'),

    path('components/', component_list_create_view, name='components'), 
    path('components/<int:id>/', component_id_detail_view, name='component-detail'),


    path('accessories/', accessory_list_create_view, name='accessories'),
    path('accessories/<int:id>/', accessory_id_detail_view, name='accessory-detail'),

    path('consumables/', consumable_list_create_view, name="consumables"),
    path('consumables/<int:id>/', consumable_id_detail_view, name='consumable-detail'),

]