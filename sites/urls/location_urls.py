from django.urls import path

from sites.api.viewsets import location_viewsets




urlpatterns = [
    # --- Locations ---
    path( "", location_viewsets.LocationViewSet.as_view( {"get": "list", "post": "create"} ), name="locations", ),
    path( "list/", location_viewsets.LocationViewSet.as_view( {"get": "list"}, pagination_class=None, ), name="locations-list", ),
    path( "<str:public_id>/", location_viewsets.LocationViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }), name="location-detail", ),
    path( "<str:public_id>/dashboard/", location_viewsets.LocationDashboardView.as_view(), name="location-dashboard", ),
        
    # --- Location Rooms ---
    path( "<str:public_id>/rooms/", location_viewsets.LocationRoomsView.as_view({"get": "list"}), name="location-rooms", ),
    path( "<str:public_id>/rooms-light/", location_viewsets.LocationRoomsView.as_view({"get": "list"},pagination_class=None,), name="location-rooms-light", ),

    # --- Location Users ---
    path( "<str:public_id>/users/", location_viewsets.LocationUsersView.as_view({"get": "list"}), name="location-users", ),
    path( "<str:public_id>/users-light/", location_viewsets.LocationUsersView.as_view({"get": "list"},pagination_class=None,), name="location-users-light", ),

    # --- Location Equipment ---
    path( "<str:public_id>/equipment/", location_viewsets.LocationEquipmentView.as_view({"get": "list"}), name="location-equipment", ),
    path( "<str:public_id>/equipment/dashboard/", location_viewsets.LocationEquipmentDashboardView.as_view(), name="location-equipment-dashboard", ),
    path( "<str:public_id>/equipment-light/", location_viewsets.LocationEquipmentView.as_view({"get": "list"},pagination_class=None,), name="location-equipment-light", ),
    # --- Location Consumables ---
    path( "<str:public_id>/consumables/", location_viewsets.LocationConsumablesView.as_view({"get": "list"}), name="location-consumables", ),
    path( "<str:public_id>/consumables/dashboard/", location_viewsets.LocationConsumableDashboardView.as_view(), name="location-consumables-dashboard", ),
    path( "<str:public_id>/consumables-light/", location_viewsets.LocationConsumablesView.as_view({"get": "list"},pagination_class=None,), name="location-consumables-light", ),

    # --- Location Accessories ---
    path( "<str:public_id>/accessories/", location_viewsets.LocationAccessoriesView.as_view({"get": "list"},pagination_class=None,), name="location-accessories", ),
    path( "<str:public_id>/accessories/dashboard/", location_viewsets.LocationAccessoryDashboardView.as_view(), name="location-accessories-dashboard", ),
    path( "<str:public_id>/accessories-light/", location_viewsets.LocationAccessoriesView.as_view({"get": "list"},pagination_class=None,), name="location-accessories-light", ),
    # --- Location Components ---
    path( "<str:public_id>/components/", location_viewsets.LocationComponentsViewSet.as_view({"get": "list"}), name="location-components", ),
    path( "<str:public_id>/components-light/", location_viewsets.LocationComponentsViewSet.as_view({"get": "list"},pagination_class=None,), name="location-components-light", ),

    # --- Location Roles ---
    path( "<str:public_id>/roles/", location_viewsets.LocationRolesViewSet.as_view({"get": "list"}), name="location-roles", ),
]