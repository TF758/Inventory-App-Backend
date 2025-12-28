from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [

    path("auth/", include("db_inventory.urls.auth_urls")),

 
    path('login/',api_login_view, name='login'),
    path('logout/',api_logout, name='logout'),
    path('refresh/', api_token_refresh, name='session_refresh'),

    path('users/create-full/', create_full_user_view, name='create-full-user'),
    path('users/', user_list_create_view, name='users'),
    path('users/<str:public_id>/',user_id_detail_view, name='user-detail'),
     path('user-locations/', user_location_list_create_view, name='userlocation-list-create'),
    path('user-locations/<str:public_id>/', user_location_id_detail_view, name='userlocation-detail'),
    path('user-locations/users/<str:public_id>/', user_location_by_user_view, name='userlocation-by-user'),
    path('unallocated-users/', unallocated_user_list_view, name='unallocated-user-list'),

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
     path("accessories-validate-import/", accessory_batch_validate_view, name="accessories-validate-import"),
    path("accessories-import/", accessory_batch_import_view, name="accessories-import"),

    path('consumables/', consumable_list_create_view, name="consumables"),
    path('consumables/<str:public_id>/', consumable_id_detail_view, name='consumable-detail'),
    path('consumables-import/', consumable_batch_import_view, name='consumables-batch-import'),
    path('consumables-validate-import/', consumable_batch_validate_view, name='consumables-batch-validate'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('roles/', role_assignment_list_create_view, name='role-assignment-list-create'),
    path('roles/<str:public_id>/', role_detail_view, name='role-detail'),

    # User-specific roles
    path('my-roles/', my_role_list, name='my-role-list'),
    path('roles/users/<str:public_id>/', user_role_list, name='user-role-list'),

    # Active role
    path('roles/me/active-role/', my_active_role, name='my-active-role'),
    path('roles/me/active-role/<str:role_id>/', my_active_role, name='my-active-role-update'),


    path('serializer-fields/',serializer_parameters_view , name='get-serializer-fields'),

    # User submits temp password + new password to complete reset

    path('password-reset/request/', password_reset_request, name='password-reset-request'),
    path('password-reset/confirm/', password_reset_confirmation, name='password-reset-confirm'),
    path('password-change/', password_change, name='password_change'),

    # used to confirm validity of password reset token
    path("reset-password/validate-token/", password_reset_validate, name="password-reset-validate"),

    # assignment
    path("assets/equipment/assign/", assign_equipment, name="assign-equipment"),
    path("assets/equipment/unassign/", unassign_equipment, name="unassign-equipment"),
     path("assets/equipment/reassign/", reassign_equipment, name="reassign-equipment"),



]