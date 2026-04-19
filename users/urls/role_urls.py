from django.urls import path
from users.api.viewsets import role_viewsets



urlpatterns = [

    # ----------------------------
    # Roles
    # ----------------------------

    path("<str:public_id>/", role_viewsets.RoleAssignmentViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="role-detail"),

    path("my-roles/", role_viewsets.UserRoleList.as_view(), name="my-role-list"),
    path("users/<str:public_id>/", role_viewsets.UserRoleList.as_view(), name="user-role-list"),

    path("me/active-role/", role_viewsets.ActiveRoleViewSet.as_view({
        "get": "retrieve",
        "put": "update"
    }), name="my-active-role"),

    path("me/active-role/<str:role_id>/", role_viewsets.ActiveRoleViewSet.as_view({
        "get": "retrieve",
        "put": "update"
    }), name="my-active-role-update"),

    path("", role_viewsets.RoleAssignmentViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="role-assignment-list-create"),
]