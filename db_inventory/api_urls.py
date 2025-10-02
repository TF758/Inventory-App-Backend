from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .viewsets import general_viewsets



urlpatterns = [

    path('login/',api_login_view, name='custom_login'),
    path('logout/',api_logout, name='logout'),
    path('refresh/', api_token_refresh, name='token_refresh'),

    path('users/', user_list_create_view, name='users'),
    path('users/<str:public_id>/',user_id_detail_view, name='user-detail'),

    path("departments/", include("db_inventory.urls.department_urls")),

    path("locations/", include("db_inventory.urls.location_urls")),

    path("rooms/", include("db_inventory.urls.room_urls")),



    path('equipments/', equipment_list_create_view, name='equipments'),
    path('equipments/<str:public_id>/', equipment_id_detail_view, name='equipment-detail'),
    path('equipments-import/', equipment_batch_import_view, name='equipment-batch-import'),
     path('equipments-validate-import/', equipment_batch_validate_view, name='equipment-batch-validate'),

    path('components/', component_list_create_view, name='components'), 
    path('components/<str:public_id>/', component_id_detail_view, name='component-detail'),


    path('accessories/', accessory_list_create_view, name='accessories'),
    path('accessories/<str:public_id>/', accessory_id_detail_view, name='accessory-detail'),

    path('consumables/', consumable_list_create_view, name="consumables"),
    path('consumables/<str:public_id>/', consumable_id_detail_view, name='consumable-detail'),
    path('consumables-import/', consumable_batch_import_view, name='consumables-batch-import'),
    path('consumables-validate-import/', consumable_batch_validate_view, name='consumables-batch-validate'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    path('roles/',my_role_list , name='my-role-list'),
    path('roles/<str:public_id>',role_detial_view , name='role-detail'),


    path("roles/me/active-role/", my_active_role, name="my-active-role"),
    path("roles/me/active-role/<str:role_id>/", my_active_role, name="my-active-role-update"),

    path('roles/users/<str:public_id>',user_role_list , name='user-role-list'),

    path('serializer-fields/',serializer_parameters_view , name='get-serializer-fields'),


]