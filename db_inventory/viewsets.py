from . import api_views

user_list_create_view = api_views.UserModelViewSet.as_view({'get': 'list', 'post':'create'})

user_id_detail_view = api_views.UserModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

department_list_create_view = api_views.DepartmentModelViewSet.as_view({'get': 'list', 'post':'create'})

department_users_view = api_views.DepartmentUsersView.as_view({'get': 'list',})

department_locations_view = api_views.DepartmentLocationsView.as_view({'get': 'list',})

department_equipment_view = api_views.DepartmentEquipmentView.as_view({'get': 'list',})

department_consumables_view = api_views.DepartmentConsumablesView.as_view({'get': 'list',})

department_accessories_view = api_views.DepartmentAccessoriesView.as_view({'get': 'list',})

department_id_detail_view = api_views.DepartmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

location_list_create_view = api_views.LocationModelViewSet.as_view({'get': 'list', 'post':'create'})

location_id_detail_view = api_views.LocationModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

location_rooms_view = api_views.LocationRoomsView.as_view({'get': 'list'})

locations_users_view = api_views.LocationUsersView.as_view({'get': 'list'})

locations_equipment_view = api_views.LocationEquipmentView.as_view({'get': 'list'})

location_consumables_view = api_views.LocationConsumablesView.as_view({'get': 'list'})

location_accessories_view = api_views.LocationAccessoriesView.as_view({'get': 'list'})

room_list_create_view = api_views.RoomModelViewSet.as_view({'get': 'list', 'post':'create'})

room_id_detail_view = api_views.RoomModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

room_users_view = api_views.RoomUsersView.as_view({'get': 'list'})

room_equipment_view = api_views.RoomEquipmentView.as_view({'get': 'list'})

room_consumables_view = api_views.RoomConsumablesView.as_view({'get': 'list'})

room_accessories_view = api_views.RoomAccessoriesView.as_view({'get': 'list'})

room_components_view = api_views.RoomComponentsView.as_view({'get': 'list'})



equipment_list_create_view = api_views.EquipmentModelViewSet.as_view({'get': 'list', 'post':'create'})

equipment_id_detail_view = api_views.EquipmentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

component_list_create_view = api_views.ComponentModelViewSet.as_view({'get': 'list', 'post':'create'})
component_id_detail_view = api_views.ComponentModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

accessory_list_create_view = api_views.AccessoryModelViewSet.as_view({'get': 'list', 'post':'create'})
accessory_id_detail_view = api_views.AccessoryModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

consumable_list_create_view = api_views.ConsumableModelViewSet.as_view({'get': 'list', 'post':'create'})
consumable_id_detail_view = api_views.ConsumableModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})