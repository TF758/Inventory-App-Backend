from django.urls import path

from db_inventory.viewsets.sites import location_viewsets


urlpatterns = [
    # --- Locations ---
    path( "", location_viewsets.LocationModelViewSet.as_view({ "get": "list", "post": "create", }), name="locations", ),
    path( "list/", location_viewsets.LocationListViewSet.as_view({ "get": "list", }), name="locations-list", ),
    path( "<str:public_id>/", location_viewsets.LocationModelViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }), name="location-detail", ),
        
    # --- Location Rooms ---
    path( "<str:public_id>/rooms-full/", location_viewsets.LocationRoomsView.as_view({"get": "list"}), name="location-rooms", ),
    path( "<str:public_id>/rooms-light/", location_viewsets.LocationRoomsMiniViewSet.as_view({"get": "list"}), name="location-rooms-light", ),

    # --- Location Users ---
    path( "<str:public_id>/users-full/", location_viewsets.LocationUsersView.as_view({"get": "list"}), name="location-users", ),
    path( "<str:public_id>/users-light/", location_viewsets.LocationUsersMiniViewSet.as_view({"get": "list"}), name="location-users-light", ),

    # --- Location Equipment ---
    path( "<str:public_id>/equipment-full/", location_viewsets.LocationEquipmentView.as_view({"get": "list"}), name="location-equipment", ),
    path( "<str:public_id>/equipment-light/", location_viewsets.LocationEquipmentMiniViewSet.as_view({"get": "list"}), name="location-equipment-light", ),
    # --- Location Consumables ---
    path( "<str:public_id>/consumables-full/", location_viewsets.LocationConsumablesView.as_view({"get": "list"}), name="location-consumables", ),
    path( "<str:public_id>/consumables-light/", location_viewsets.LocationConsumablesMiniViewSet.as_view({"get": "list"}), name="location-consumables-light", ),

    # --- Location Accessories ---
    path( "<str:public_id>/accessories-full/", location_viewsets.LocationAccessoriesView.as_view({"get": "list"}), name="location-accessories", ),
    path( "<str:public_id>/accessories-light/", location_viewsets.LocationAccessoriesMiniViewSet.as_view({"get": "list"}), name="location-accessories-light", ),
    # --- Location Components ---
    path( "<str:public_id>/components-full/", location_viewsets.LocationComponentsViewSet.as_view({"get": "list"}), name="location-components", ),
    path( "<str:public_id>/components-light/", location_viewsets.LocationComponentsMiniViewSet.as_view({"get": "list"}), name="location-components-light", ),

    # --- Location Roles ---
    path( "<str:public_id>/roles/", location_viewsets.LocationRolesViewSet.as_view({"get": "list"}), name="location-roles", ),
]