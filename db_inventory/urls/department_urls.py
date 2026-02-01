from django.urls import path

from db_inventory.viewsets.sites import department_viewsets



urlpatterns = [
    # --- Departments ---
    path( "", department_viewsets.DepartmentViewSet.as_view( {"get": "list", "post": "create"} ), name="departments", ),
    path( "list/", department_viewsets.DepartmentViewSet.as_view( {"get": "list"}, pagination_class=None, ), name="departments-list", ),
    path( "<str:public_id>/", department_viewsets.DepartmentViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }), name="department-detail", ),

    # --- Department Users ---
    path( "<str:public_id>/users/", department_viewsets.DepartmentUsersViewSet.as_view({"get": "list"}), name="department-users", ),
    path("<str:public_id>/users-light/", department_viewsets.DepartmentUsersViewSet.as_view( {"get": "list"}, pagination_class=None,), name="department-users-light", ),

    # --- Department Locations ---
    path( "<str:public_id>/locations/", department_viewsets.DepartmentLocationsViewSet.as_view({"get": "list"}), name="department-locations", ),
    path( "<str:public_id>/locations-light/", department_viewsets.DepartmentLocationsViewSet.as_view( {"get": "list"}, pagination_class=None,), name="department-locations-light", ),
    # --- Department Equipment ---
    path( "<str:public_id>/equipment/", department_viewsets.DepartmentEquipmentViewSet.as_view({"get": "list"}), name="department-equipment", ),
    path( "<str:public_id>/equipment/dashboard/", department_viewsets.DepartmentEquipmentDashboardView.as_view(), name="department-equipment-dashboard", ),
    path( "<str:public_id>/equipment-light/", department_viewsets.DepartmentEquipmentViewSet.as_view({"get": "list"},pagination_class=None,), name="department-equipment-light", ),
    # --- Department Consumables ---
    path( "<str:public_id>/consumables/", department_viewsets.DepartmentConsumablesViewSet.as_view({"get": "list"}), name="department-consumables", ),
    path( "<str:public_id>/consumables/dashboard/", department_viewsets.DepartmentConsumableDashboardView.as_view(), name="department-consumables-dashboard", ),
    path( "<str:public_id>/consumables-light/", department_viewsets.DepartmentConsumablesViewSet.as_view({"get": "list"}, pagination_class=None,), name="department-consumables-light", ),

    # --- Department Accessories ---
    path( "<str:public_id>/accessories/", department_viewsets.DepartmentAccessoriesViewSet.as_view({"get": "list"}), name="department-accessories", ),
    path( "<str:public_id>/accessories/dashboard/", department_viewsets.DepartmentAccessoryDashboardView.as_view(), name="department-accessories-dashboard", ),
    path( "<str:public_id>/accessories-light/", department_viewsets.DepartmentAccessoriesViewSet.as_view({"get": "list"}, pagination_class=None,), name="department-accessories-light", ),

    # --- Department Components ---
    path( "<str:public_id>/components/", department_viewsets.DepartmentComponentsViewSet.as_view({"get": "list"}), name="department-components", ),
    path( "<str:public_id>/components-light/", department_viewsets.DepartmentComponentsMiniViewSet.as_view({"get": "list"}, pagination_class=None,), name="department-components-light", ),

    # --- Department Roles ---
    path( "<str:public_id>/roles/", department_viewsets.DepartmentRolesViewSet.as_view({"get": "list"}), name="department-roles", ),

    # --- Department Rooms ---
    path( "<str:public_id>/rooms-full/", department_viewsets.DepartmentRoomsViewSet.as_view({"get": "list"}), name="department-rooms", ), 
    
]