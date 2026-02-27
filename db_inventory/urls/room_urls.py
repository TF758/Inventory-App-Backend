from django.urls import path

from db_inventory.viewsets.sites import room_viewsets





urlpatterns = [
    # --- Rooms ---
    path( "", room_viewsets.RoomViewSet.as_view({"get": "list", "post": "create"}), name="rooms", ),
    path( "list/", room_viewsets.RoomViewSet.as_view( {"get": "list"}, pagination_class=None, ), name="rooms-list", ),
    path( "<str:public_id>/", room_viewsets.RoomViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }), name="room-detail", ),
    path( "<str:public_id>/dashboard/", room_viewsets.RoomDashboardView.as_view(), name="room-dashboard", ),

    # --- Room Users ---
    path( "<str:public_id>/users/", room_viewsets.RoomUsersViewSet.as_view({"get": "list"}), name="room-users", ),
    path( "<str:public_id>/users-light/", room_viewsets.RoomUsersViewSet.as_view({"get": "list"},pagination_class=None,), name="room-users-light", ),
    # --- Room Equipment ---
    path( "<str:public_id>/equipment/", room_viewsets.RoomEquipmentViewSet.as_view({"get": "list"}), name="room-equipment", ),
    path( "<str:public_id>/equipment/dashboard/", room_viewsets.RoomEquipmentDashboardView.as_view(), name="room-equipment-dashboard", ),
    path( "<str:public_id>/equipment-light/", room_viewsets.RoomEquipmentViewSet.as_view({"get": "list"},pagination_class=None,), name="room-equipment-light", ),
    # --- Room Consumables ---
    path( "<str:public_id>/consumables/", room_viewsets.RoomConsumablesViewSet.as_view({"get": "list"}), name="room-consumables", ),
    path( "<str:public_id>/consumables/dashboard/", room_viewsets.RoomConsumableDashboardView.as_view(), name="room-consumables-dashboard", ),
    path( "<str:public_id>/consumables-light/", room_viewsets.RoomConsumablesViewSet.as_view({"get": "list"},pagination_class=None,), name="room-consumables-light", ),

    # --- Room Accessories ---
    path( "<str:public_id>/accessories/", room_viewsets.RoomAccessoriesViewSet.as_view({"get": "list"}), name="room-accessories", ),
    path( "<str:public_id>/accessories/dashboard/", room_viewsets.RoomAccessoryDashboardView.as_view(), name="room-accessories-dashboard", ),
    path( "<str:public_id>/accessories-light/", room_viewsets.RoomAccessoriesViewSet.as_view({"get": "list"},pagination_class=None,), name="room-accessories-light", ),

    # --- Room Components ---
    path( "<str:public_id>/components/", room_viewsets.RoomComponentsViewSet.as_view({"get": "list"}), name="room-components", ),
    path( "<str:public_id>/components-light/", room_viewsets.RoomComponentsViewSet.as_view({"get": "list"},pagination_class=None,), name="room-components-light", ),

    # --- Room Roles ---
    path( "<str:public_id>/roles/", room_viewsets.RoomRolesViewSet.as_view({"get": "list"}), name="room-roles", ),
]