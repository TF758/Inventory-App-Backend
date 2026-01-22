from django.urls import path, include

from .viewsets import *

"""
API URL structure:

- CRUD inventory records: /equipments, /accessories, /consumables
- Inventory operations (assign, use, restock, events): /inventory/...
- phsyical site structure: /departments, /locations, /rooms
"""

urlpatterns = [

    path("auth/", include("db_inventory.urls.auth_urls")),
    path("inventory/", include("db_inventory.urls.inventory_urls")),

    path("", include("db_inventory.notifications.urls")),

 
    path('login/', general_viewsets.SessionTokenLoginView.as_view(), name='login'),
    path('logout/', general_viewsets.LogoutAPIView.as_view(), name='logout'),
    path('refresh/', general_viewsets.RefreshAPIView.as_view(), name='session_refresh'),

    path('users/create-full/', user_viewsets.FullUserCreateView.as_view(), name='create-full-user'),
    path('users/', user_viewsets.UserModelViewSet.as_view({'get': 'list', 'post':'create'}), name='users'),
    path('users/<str:public_id>/',user_viewsets.UserModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
        }), name='user-detail'),

    path('user-locations/', user_viewsets.UserLocationViewSet.as_view({'get': 'list', 'post':'create'}), name='userlocation-list-create'),
    path('user-locations/<str:public_id>/', user_viewsets.UserLocationViewSet.as_view({  
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='userlocation-detail'),
    path('user-locations/users/<str:public_id>/', user_viewsets.UserLocationByUserView.as_view(), name='userlocation-by-user'),
    path('unallocated-users/', user_viewsets.UnallocatedUserViewSet.as_view({'get': 'list'}), name='unallocated-user-list'),

    path("departments/", include("db_inventory.urls.department_urls")),

    path("locations/", include("db_inventory.urls.location_urls")),

    path("rooms/", include("db_inventory.urls.room_urls")),


    path('equipments/', equipment_viewsets.EquipmentModelViewSet.as_view({'get': 'list', 'post':'create'}), name='equipments'),
    path('equipments/<str:public_id>/', equipment_viewsets.EquipmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
        }), name='equipment-detail'),

    path('equipments/<str:public_id>/status/', equipment_viewsets.EquipmentStatusChangeView.as_view(), name='update-equipment-status'),
    path('equipments-import/', equipment_viewsets.EquipmentBatchImportView.as_view(), name='equipment-batch-import'),
    path('equipments-validate-import/', equipment_viewsets.EquipmentBatchValidateView.as_view(), name='equipment-batch-validate'),
    

    path('components/', component_viewsets.ComponentModelViewSet.as_view({'get': 'list', 'post':'create'}),name='components'), 
    path('components/<str:public_id>/', component_viewsets.ComponentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
        }), name='component-detail'),


    path('accessories/', accessory_viewsets.AccessoryModelViewSet.as_view({'get': 'list', 'post':'create'}), name='accessories'),
    path('accessories/<str:public_id>/', accessory_viewsets.AccessoryModelViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }), name='accessory-detail'),

    path("accessories-validate-import/",  accessory_viewsets.AccessoryBatchValidateView.as_view(), name="accessories-validate-import"),
    path("accessories-import/",  accessory_viewsets.AccessoryBatchImportView.as_view(), name="accessories-import"),

    path('consumables/', consumable_viewsets.ConsumableModelViewSet.as_view({'get': 'list', 'post':'create'}), name="consumables"),
    path('consumables/<str:public_id>/', consumable_viewsets.ConsumableModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
    }), name='consumable-detail'),

    path('consumables-import/', consumable_viewsets.ConsumableBatchImportView.as_view(), name='consumables-batch-import'),
    path('consumables-validate-import/', consumable_viewsets.ConsumableBatchValidateView.as_view(), name='consumables-batch-validate'),


    path('roles/', role_viewsets.RoleAssignmentViewSet.as_view({ 'get': 'list', 'post': 'create' }), name='role-assignment-list-create'),
    path('roles/<str:public_id>/',  role_viewsets.RoleAssignmentViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
        })
    , name='role-detail'),
    # User-specific roles
    path('my-roles/', role_viewsets.UserRoleList.as_view(), name='my-role-list'),
    path('roles/users/<str:public_id>/', role_viewsets.UserRoleList.as_view()  , name='user-role-list'),

    # Active role
    path('roles/me/active-role/',role_viewsets.ActiveRoleViewSet.as_view({ 'get': 'retrieve', 'put': 'update' }), name='my-active-role'),
    path('roles/me/active-role/<str:role_id>/',role_viewsets.ActiveRoleViewSet.as_view({ 'get': 'retrieve', 'put': 'update' }), name='my-active-role-update'),


    path('serializer-fields/',general_viewsets.SerializerFieldsView.as_view() , name='get-serializer-fields'),

    # User submits temp password + new password to complete reset

    path('password-reset/request/',  general_viewsets.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', general_viewsets.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password-change/', auth_viewsets.ChangePasswordView.as_view(), name='password_change'),

    # used to confirm validity of password reset token
    path("reset-password/validate-token/", general_viewsets.PasswordResetValidateView.as_view(), name="password-reset-validate"),


]