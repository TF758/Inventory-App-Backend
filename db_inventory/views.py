from .viewsets import user_viewsets, department_viewsets, location_viewsets, room_viewsets, equipment_viewsets,component_viewsets,consumable_viewsets, accessory_viewsets, general_viewsets, role_viewsets



api_login_view = general_viewsets.CustomTokenObtainPairView.as_view()
api_token_refresh = general_viewsets.CookieTokenRefreshView.as_view()
api_logout = general_viewsets.LogoutAPIView.as_view()

user_list_create_view = user_viewsets.UserModelViewSet.as_view({'get': 'list', 'post':'create'})

user_id_detail_view = user_viewsets.UserModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

my_role_list = general_viewsets.MyRoleList.as_view()
role_detial_view = general_viewsets.RoleDetailView.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
user_role_switch = general_viewsets.RoleSwitchView.as_view()
user_role_list = general_viewsets.UserRoleListView.as_view()

my_active_role = role_viewsets.ActiveRoleViewSet.as_view({'get': 'retrieve', 'put': 'update'})

department_list_create_view = department_viewsets.DepartmentModelViewSet.as_view({'get': 'list', 'post':'create'})
department_list_view = department_viewsets.DepartmentListViewSet.as_view({'get': 'list',})

department_users_view = department_viewsets.DepartmentUsersViewSet.as_view({'get': 'list',})
department_users_light_view = department_viewsets.DepartmentUsersMiniViewSet.as_view({'get': 'list',})

department_locations_view = department_viewsets.DepartmentLocationsViewSet.as_view({'get': 'list',})
department_locations_light_view = department_viewsets.DepartmentLocationsMiniViewSet.as_view({'get': 'list',})

department_equipment_view = department_viewsets.DepartmentEquipmentViewSet.as_view({'get': 'list',})
department_equipment_light_view = department_viewsets.DepartmentEquipmentMiniViewSet.as_view({'get': 'list',})

department_consumables_view = department_viewsets.DepartmentConsumablesViewSet.as_view({'get': 'list',})
department_consumables_light_view = department_viewsets.DepartmentConsumablesMiniViewSet.as_view({'get': 'list',})

department_accessories_view = department_viewsets.DepartmentAccessoriesViewSet.as_view({'get': 'list',})
department_accessories_light_view = department_viewsets.DepartmentAccessoriesMiniViewSet.as_view({'get': 'list',})

department_components_view = department_viewsets.DepartmentComponentsViewSet.as_view({'get': 'list',})
department_components_light_view = department_viewsets.DepartmentComponentsMiniViewSet.as_view({'get': 'list',})

department_detail_view = department_viewsets.DepartmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

location_list_create_view = location_viewsets.LocationModelViewSet.as_view({'get': 'list', 'post':'create'})
location_list_view = location_viewsets.LocationListViewSet.as_view({'get': 'list'})

location_id_detail_view = location_viewsets.LocationModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

location_rooms_view = location_viewsets.LocationRoomsView.as_view({'get': 'list'})
location_rooms_light_view = location_viewsets.LocationRoomsMiniViewSet.as_view({'get': 'list'})

locations_users_view = location_viewsets.LocationUsersView.as_view({'get': 'list'})
locations_users_light_view = location_viewsets.LocationUsersMiniViewSet.as_view({'get': 'list'})


locations_equipment_view = location_viewsets.LocationEquipmentView.as_view({'get': 'list'})
locations_equipment_light_view = location_viewsets.LocationEquipmentMiniViewSet.as_view({'get': 'list'})

location_consumables_view = location_viewsets.LocationConsumablesView.as_view({'get': 'list'})
location_consumables_light_view = location_viewsets.LocationConsumablesMiniViewSet.as_view({'get': 'list'})

location_accessories_view = location_viewsets.LocationAccessoriesView.as_view({'get': 'list'})
location_accessories_light_view = location_viewsets.LocationAccessoriesMiniViewSet.as_view({'get': 'list'})


room_list_create_view = room_viewsets.RoomModelViewSet.as_view({'get': 'list', 'post':'create'})
room_list_view = room_viewsets.RoomListViewset.as_view({'get': 'list'})

room_id_detail_view = room_viewsets.RoomModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

room_users_view = room_viewsets.RoomUsersViewSet.as_view({'get': 'list'})
room_users_light_view = room_viewsets.RoomUsersMiniViewSet.as_view({'get': 'list'})

room_equipment_view = room_viewsets.RoomEquipmentViewSet.as_view({'get': 'list'})
room_equipment_light_view = room_viewsets.RoomEquipmentMiniViewSet.as_view({'get': 'list'})

room_consumables_view = room_viewsets.RoomConsumablesViewSet.as_view({'get': 'list'})
room_consumables_light_view = room_viewsets.RoomConsumablesMiniViewSet.as_view({'get': 'list'})

room_accessories_view = room_viewsets.RoomAccessoriesViewSet.as_view({'get': 'list'})
room_accessories_light_view = room_viewsets.RoomAccessoriesMiniViewSet.as_view({'get': 'list'})

room_components_view = room_viewsets.RoomComponentsViewSet.as_view({'get': 'list'})
room_components_light_view = room_viewsets.RoomComponentsMiniViewSet.as_view({'get': 'list'})



equipment_list_create_view = equipment_viewsets.EquipmentModelViewSet.as_view({'get': 'list', 'post':'create'})

equipment_id_detail_view = equipment_viewsets.EquipmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

component_list_create_view = component_viewsets.ComponentModelViewSet.as_view({'get': 'list', 'post':'create'})
component_id_detail_view = component_viewsets.ComponentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

accessory_list_create_view = accessory_viewsets.AccessoryModelViewSet.as_view({'get': 'list', 'post':'create'})
accessory_id_detail_view = accessory_viewsets.AccessoryModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

consumable_list_create_view = consumable_viewsets.ConsumableModelViewSet.as_view({'get': 'list', 'post':'create'})
consumable_id_detail_view = consumable_viewsets.ConsumableModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})