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

room_list_create_view = api_views.RoomModelViewSet.as_view({'get': 'list', 'post':'create'})

room_id_detail_view = api_views.RoomModelViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})





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