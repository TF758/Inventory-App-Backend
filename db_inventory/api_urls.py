from django.urls import path
from . import api_views
from  db_inventory.viewsets import *


urlpatterns = [
    # path('users/', api_views.ListUserView.as_view(), name='api-users'),
    path('users/', user_list_create_view, name='users'),
    path('users/<int:id>/',user_id_detail_view, name='user-detail'),

    path('departments/', department_list_create_view, name='departments'),
    path('departments/<int:id>/', department_id_detail_view, name='department-detail'),

    path('departments/<int:id>/users/', api_views.DepartmentUsersView.as_view(), name='department-users'),
    path('departments/<int:id>/equipment/', api_views.DepartmentEquipmentsView.as_view(), name='department-equipments'),


    path('locations/',location_list_create_view, name='locations'),
    path('locations/<int:id>/', location_id_detail_view , name='location-detail'),
    path('locations/<int:id>/equipment/', api_views.LocationEquipmentsView.as_view(), name='location-equipments'),

    path('equipments/', equipment_list_create_view, name='equipments'),
    path('equipments/<int:id>/', equipment_id_detail_view, name='equipment-detail'),

    path('components/', component_list_create_view, name='components'), 
    path('components/<int:id>/', component_id_detail_view, name='component-detail'),
    path('components/<int:id>/equipment/', api_views.ComponentEquipmentsView.as_view(), name='component-equipments'),

    path('accessories/', accessory_list_create_view, name='accessories'),
    path('accessories/<int:id>/', accessory_id_detail_view, name='accessory-detail'),
]