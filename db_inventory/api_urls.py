from django.urls import path, include



from .viewsets import *

"""
API URL structure:

- CRUD inventory records: /equipments, /accessories, /consumables
- Inventory operations (assign, use, restock, events): /inventory/...
- phsyical site structure: /departments, /locations, /rooms
"""

urlpatterns = [

    # ----------------------------
    # Core Modules
    # ----------------------------
    path("auth/", include("db_inventory.urls.auth_urls")),
    path("inventory/", include("db_inventory.urls.inventory_urls")),
    path("departments/", include("db_inventory.urls.department_urls")),
    path("locations/", include("db_inventory.urls.location_urls")),
    path("rooms/", include("db_inventory.urls.room_urls")),
    path("users/", include("db_inventory.urls.user_urls")), 

    path("", include("db_inventory.notifications.urls")),

    # ----------------------------
    # Auth / Session
    # ----------------------------
    path("login/", general_viewsets.SessionTokenLoginView.as_view(), name="login"),
    path("logout/", general_viewsets.LogoutAPIView.as_view(), name="logout"),
    path("refresh/", general_viewsets.RefreshAPIView.as_view(), name="session_refresh"),

    # ----------------------------
    # Equipment
    # ----------------------------
    path("equipments/", equipment_viewsets.EquipmentModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="equipments"),

    # --- batch routes FIRST ---
    path("equipment/batch-unassign/", BatchUnassignEquipmentView.as_view(), name="batch-unassign-equipment"),
    path("equipment/batch-assign/", BatchAssignEquipmentView.as_view(), name="batch-assign-equipment"),
    path("equipment/batch-condemn/", BatchEquipmentCondemnView.as_view(), name="batch-condemn-equipment"),
    path("equipment/batch-status-change/", BatchEquipmentStatusChangeView.as_view(), name="batch-equipment-status-change"),
    path("equipment/batch-soft-delete/", BatchEquipmentSoftDeleteView.as_view(), name="batch-equipment-soft-delete"),

    path("equipments-import/", equipment_viewsets.EquipmentBatchImportView.as_view(), name="equipment-batch-import"),

    path("equipments/<str:public_id>/status/", equipment_viewsets.EquipmentStatusChangeView.as_view(), name="update-equipment-status"),
    path("equipments/<str:public_id>/condemn/", equipment_viewsets.EquipmentCondemnView.as_view(), name="condemn-equipment"),
    path("equipments/<str:public_id>/restore/", equipment_viewsets.EquipmentRestoreViewSet.as_view(), name="restore-equipment"),
    path("equipments/<str:public_id>/soft-delete/", equipment_viewsets.EquipmentSoftDeleteView.as_view(), name="soft-delete-equipment"),

    path("equipments/<str:public_id>/", equipment_viewsets.EquipmentModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="equipment-detail"),

    # ----------------------------
    # Components
    # ----------------------------
    path("components/", component_viewsets.ComponentModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="components"),

    path("components/<str:public_id>/", component_viewsets.ComponentModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="component-detail"),

    # ----------------------------
    # Accessories
    # ----------------------------
    path("accessories/", accessory_viewsets.AccessoryModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="accessories"),

    path("accessory/batch-soft-delete/", accessory_viewsets.BatchAccessorySoftDeleteView.as_view(), name="batch-soft-delete-accessory"),
    path("accessory/batch-hard-delete/", accessory_viewsets.BatchAccessoryHardDeleteView.as_view(), name="batch-hard-delete-accessory"),

    path("accessories/<str:public_id>/restore/", accessory_viewsets.AccessoryRestoreViewSet.as_view(), name="restore-accessory"),
    path("accessories/<str:public_id>/soft-delete/", accessory_viewsets.AccessorySoftDeleteView.as_view(), name="soft-delete-accessory"),

    path("accessories/<str:public_id>/", accessory_viewsets.AccessoryModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="accessory-detail"),

    path("accessories-validate-import/", accessory_viewsets.AccessoryBatchValidateView.as_view(), name="accessories-validate-import"),
    path("accessories-import/", accessory_viewsets.AccessoryBatchImportView.as_view(), name="accessories-import"),

    # ----------------------------
    # Consumables
    # ----------------------------
    path("consumables/", consumable_viewsets.ConsumableModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="consumables"),

    path("consumable/batch-soft-delete/", consumable_viewsets.BatchConsumableSoftDeleteView.as_view(), name="batch-soft-delete-consumable"),
    path("consumable/batch-hard-delete/", consumable_viewsets.BatchConsumableHardDeleteView.as_view(), name="batch-hard-delete-consumable"),

    path("consumables/<str:public_id>/restore/", consumable_viewsets.ConsumableRestoreViewSet.as_view(), name="restore-consumable"),
    path("consumables/<str:public_id>/soft-delete/", consumable_viewsets.ConsumableSoftDeleteView.as_view(), name="soft-delete-consumable"),

    path("consumables/<str:public_id>/", consumable_viewsets.ConsumableModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="consumable-detail"),

    path("consumables-import/", consumable_viewsets.ConsumableBatchImportView.as_view(), name="consumables-batch-import"),
    path("consumables-validate-import/", consumable_viewsets.ConsumableBatchValidateView.as_view(), name="consumables-batch-validate"),

    # ----------------------------
    # Roles
    # ----------------------------
    path("roles/", role_viewsets.RoleAssignmentViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="role-assignment-list-create"),

    path("roles/<str:public_id>/", role_viewsets.RoleAssignmentViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="role-detail"),

    path("my-roles/", role_viewsets.UserRoleList.as_view(), name="my-role-list"),
    path("roles/users/<str:public_id>/", role_viewsets.UserRoleList.as_view(), name="user-role-list"),

    path("roles/me/active-role/", role_viewsets.ActiveRoleViewSet.as_view({
        "get": "retrieve",
        "put": "update"
    }), name="my-active-role"),

    path("roles/me/active-role/<str:role_id>/", role_viewsets.ActiveRoleViewSet.as_view({
        "get": "retrieve",
        "put": "update"
    }), name="my-active-role-update"),

    # ----------------------------
    # Utility
    # ----------------------------
    path("serializer-fields/", general_viewsets.SerializerFieldsView.as_view(), name="get-serializer-fields"),

    # ----------------------------
    # Password Reset
    # ----------------------------
    path("password-reset/request/", general_viewsets.PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", general_viewsets.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", general_viewsets.ChangePasswordView.as_view(), name="password_change"),
    path("reset-password/validate-token/", general_viewsets.PasswordResetValidateView.as_view(), name="password-reset-validate"),
]