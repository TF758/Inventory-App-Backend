from inventory_metrics.viewsets import admin_metrics_viewset
from .viewsets import (
    user_viewsets,
    department_viewsets,
    location_viewsets,
    room_viewsets,
    equipment_viewsets,
    component_viewsets,
    consumable_viewsets,
    accessory_viewsets,
    general_viewsets,
    role_viewsets,
    auth_viewsets
)

# --- General ---
api_login_view = general_viewsets.SessionTokenLoginView.as_view()
api_logout = general_viewsets.LogoutAPIView.as_view()
api_token_refresh = general_viewsets.RefreshAPIView.as_view()

# --- Accessory ---
accessory_batch_import_view = accessory_viewsets.AccessoryBatchImportView.as_view()
accessory_batch_validate_view = accessory_viewsets.AccessoryBatchValidateView.as_view()
accessory_id_detail_view = accessory_viewsets.AccessoryModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
accessory_list_create_view = accessory_viewsets.AccessoryModelViewSet.as_view({'get': 'list', 'post':'create'})

# --- Component ---
component_id_detail_view = component_viewsets.ComponentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
component_list_create_view = component_viewsets.ComponentModelViewSet.as_view({'get': 'list', 'post':'create'})

# --- Consumable ---
consumable_batch_import_view = consumable_viewsets.ConsumableBatchImportView.as_view()
consumable_batch_validate_view = consumable_viewsets.ConsumableBatchValidateView.as_view()
consumable_id_detail_view = consumable_viewsets.ConsumableModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
consumable_list_create_view = consumable_viewsets.ConsumableModelViewSet.as_view({'get': 'list', 'post':'create'})

# --- Department ---
department_accessories_light_view = department_viewsets.DepartmentAccessoriesMiniViewSet.as_view({'get': 'list',})
department_accessories_view = department_viewsets.DepartmentAccessoriesViewSet.as_view({'get': 'list',})
department_components_light_view = department_viewsets.DepartmentComponentsMiniViewSet.as_view({'get': 'list',})
department_components_view = department_viewsets.DepartmentComponentsViewSet.as_view({'get': 'list',})
department_consumables_light_view = department_viewsets.DepartmentConsumablesMiniViewSet.as_view({'get': 'list',})
department_consumables_view = department_viewsets.DepartmentConsumablesViewSet.as_view({'get': 'list',})
department_detail_view = department_viewsets.DepartmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
department_equipment_light_view = department_viewsets.DepartmentEquipmentMiniViewSet.as_view({'get': 'list',})
department_equipment_view = department_viewsets.DepartmentEquipmentViewSet.as_view({'get': 'list',})
department_list_create_view = department_viewsets.DepartmentModelViewSet.as_view({'get': 'list', 'post':'create'})
department_list_view = department_viewsets.DepartmentListViewSet.as_view({'get': 'list',})
department_locations_light_view = department_viewsets.DepartmentLocationsMiniViewSet.as_view({'get': 'list',})
department_locations_view = department_viewsets.DepartmentLocationsViewSet.as_view({'get': 'list',})
department_users_light_view = department_viewsets.DepartmentUsersMiniViewSet.as_view({'get': 'list',})
department_users_view = department_viewsets.DepartmentUsersViewSet.as_view({'get': 'list',})
department_roles_view = department_viewsets.DepartmentRolesViewSet.as_view({'get': 'list'})
department_rooms = department_viewsets.DepartmentRoomsViewSet.as_view({'get': 'list'})

# --- Equipment ---
equipment_batch_import_view = equipment_viewsets.EquipmentBatchImportView.as_view()
equipment_batch_validate_view = equipment_viewsets.EquipmentBatchValidateView.as_view()
equipment_id_detail_view = equipment_viewsets.EquipmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
equipment_list_create_view = equipment_viewsets.EquipmentModelViewSet.as_view({'get': 'list', 'post':'create'})

# --- Location ---
location_accessories_light_view = location_viewsets.LocationAccessoriesMiniViewSet.as_view({'get': 'list'})
location_accessories_view = location_viewsets.LocationAccessoriesView.as_view({'get': 'list'})
location_components_light_view = location_viewsets.LocationComponentsMiniViewSet.as_view({'get': 'list'})
location_components_view = location_viewsets.LocationComponentsViewSet.as_view({'get': 'list'})
location_consumables_light_view = location_viewsets.LocationConsumablesMiniViewSet.as_view({'get': 'list'})
location_consumables_view = location_viewsets.LocationConsumablesView.as_view({'get': 'list'})
location_id_detail_view = location_viewsets.LocationModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
location_list_create_view = location_viewsets.LocationModelViewSet.as_view({'get': 'list', 'post':'create'})
location_list_view = location_viewsets.LocationListViewSet.as_view({'get': 'list'})
location_rooms_light_view = location_viewsets.LocationRoomsMiniViewSet.as_view({'get': 'list'})
location_rooms_view = location_viewsets.LocationRoomsView.as_view({'get': 'list'})
locations_equipment_light_view = location_viewsets.LocationEquipmentMiniViewSet.as_view({'get': 'list'})
locations_equipment_view = location_viewsets.LocationEquipmentView.as_view({'get': 'list'})
locations_users_light_view = location_viewsets.LocationUsersMiniViewSet.as_view({'get': 'list'})
locations_users_view = location_viewsets.LocationUsersView.as_view({'get': 'list'})
location_roles_view = location_viewsets.LocationRolesViewSet.as_view({'get': 'list'})

# --- Role ---
# Active role for logged-in user
my_active_role = role_viewsets.ActiveRoleViewSet.as_view({
    'get': 'retrieve',
    'put': 'update'
})

# User role lists
my_role_list = role_viewsets.UserRoleList.as_view()  # Handles current user's roles
user_role_list = role_viewsets.UserRoleList.as_view()  # Handles any user's roles via public_id

# Role assignments CRUD
role_assignment_list_create_view = role_viewsets.RoleAssignmentViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
role_detail_view = role_viewsets.RoleAssignmentViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

# --- Room ---
room_accessories_light_view = room_viewsets.RoomAccessoriesMiniViewSet.as_view({'get': 'list'})
room_accessories_view = room_viewsets.RoomAccessoriesViewSet.as_view({'get': 'list'})
room_components_light_view = room_viewsets.RoomComponentsMiniViewSet.as_view({'get': 'list'})
room_components_view = room_viewsets.RoomComponentsViewSet.as_view({'get': 'list'})
room_consumables_light_view = room_viewsets.RoomConsumablesMiniViewSet.as_view({'get': 'list'})
room_consumables_view = room_viewsets.RoomConsumablesViewSet.as_view({'get': 'list'})
room_equipment_light_view = room_viewsets.RoomEquipmentMiniViewSet.as_view({'get': 'list'})
room_equipment_view = room_viewsets.RoomEquipmentViewSet.as_view({'get': 'list'})
room_id_detail_view = room_viewsets.RoomModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
room_list_create_view = room_viewsets.RoomModelViewSet.as_view({'get': 'list', 'post':'create'})
room_list_view = room_viewsets.RoomListViewset.as_view({'get': 'list'})
room_users_light_view = room_viewsets.RoomUsersMiniViewSet.as_view({'get': 'list'})
room_users_view = room_viewsets.RoomUsersViewSet.as_view({'get': 'list'})
room_roles_view = room_viewsets.RoomRolesViewSet.as_view({'get': 'list'})

# --- Serializer ---
serializer_parameters_view = general_viewsets.SerializerFieldsView.as_view()

# --- User ---
create_full_user_view = user_viewsets.FullUserCreateView.as_view()
user_id_detail_view = user_viewsets.UserModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
user_list_create_view = user_viewsets.UserModelViewSet.as_view({'get': 'list', 'post':'create'})

user_location_list_create_view = user_viewsets.UserLocationViewSet.as_view({'get': 'list', 'post':'create'})
user_location_id_detail_view = user_viewsets.UserLocationViewSet.as_view({  
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
# --- User Location by User ---
user_location_by_user_view = user_viewsets.UserLocationByUserView.as_view()
unallocated_user_list_view = user_viewsets.UnallocatedUserViewSet.as_view({'get': 'list'})


# ---Password Reset ----

password_reset_request = general_viewsets.PasswordResetRequestView.as_view()
password_reset_confirmation = general_viewsets.PasswordResetConfirmView.as_view()

# ---Password Change ---

password_change = auth_viewsets.ChangePasswordView.as_view()

# ---Validate Password Reset Token ---
password_reset_validate = general_viewsets.PasswordResetValidateView.as_view()

# --- User Sessions ---
user_session_revoke_all_view = auth_viewsets.RevokeUserSessionsViewset.as_view({
    'post': 'revoke_all'
})

# Lock user
user_lock_view = auth_viewsets.UserLockViewSet.as_view({
    'post': 'lock'
})

# Unlock user
user_unlock_view = auth_viewsets.UserLockViewSet.as_view({
    'post': 'unlock'
})

# Admin reset user password
admin_reset_user_password_view = auth_viewsets.AdminResetUserPasswordView.as_view()

admin_logs = auth_viewsets.AuditLogViewSet.as_view({'get': 'list'})

# rename a site
site_rename_view = auth_viewsets.SiteNameChangeAPIView.as_view()

# relocate a site
site_relocate_view = auth_viewsets.SiteRelocationAPIView.as_view()