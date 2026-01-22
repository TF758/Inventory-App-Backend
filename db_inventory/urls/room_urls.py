from django.urls import path

from db_inventory.viewsets.sites import room_viewsets





urlpatterns = [
    # --- Rooms ---
    path( "", room_viewsets.RoomModelViewSet.as_view({ "get": "list", "post": "create", }), name="rooms", ),
    path( "list/", room_viewsets.RoomListViewset.as_view({ "get": "list", }), name="rooms-list", ),
    path( "<str:public_id>/", room_viewsets.RoomModelViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }), name="room-detail", ),

    # --- Room Users ---
    path( "<str:public_id>/users-full/", room_viewsets.RoomUsersViewSet.as_view({"get": "list"}), name="room-users", ),
    path( "<str:public_id>/users-light/", room_viewsets.RoomUsersMiniViewSet.as_view({"get": "list"}), name="room-users-light", ),
    # --- Room Equipment ---
    path( "<str:public_id>/equipment-full/", room_viewsets.RoomEquipmentViewSet.as_view({"get": "list"}), name="room-equipment", ),
    path( "<str:public_id>/equipment-light/", room_viewsets.RoomEquipmentMiniViewSet.as_view({"get": "list"}), name="room-equipment-light", ),
    # --- Room Consumables ---
    path( "<str:public_id>/consumables-full/", room_viewsets.RoomConsumablesViewSet.as_view({"get": "list"}), name="room-consumables", ),
    path( "<str:public_id>/consumables-light/", room_viewsets.RoomConsumablesMiniViewSet.as_view({"get": "list"}), name="room-consumables-light", ),

    # --- Room Accessories ---
    path( "<str:public_id>/accessories-full/", room_viewsets.RoomAccessoriesViewSet.as_view({"get": "list"}), name="room-accessories", ),
    path( "<str:public_id>/accessories-light/", room_viewsets.RoomAccessoriesMiniViewSet.as_view({"get": "list"}), name="room-accessories-light", ),

    # --- Room Components ---
    path( "<str:public_id>/components-full/", room_viewsets.RoomComponentsViewSet.as_view({"get": "list"}), name="room-components", ),
    path( "<str:public_id>/components-light/", room_viewsets.RoomComponentsMiniViewSet.as_view({"get": "list"}), name="room-components-light", ),

    # --- Room Roles ---
    path( "<str:public_id>/roles/", room_viewsets.RoomRolesViewSet.as_view({"get": "list"}), name="room-roles", ),
]