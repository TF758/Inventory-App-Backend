from django.urls import path

from .views import (
    PermissionMatrixView,
    RoleListView,
    RolePermissionsView,
    RolePermissionsUpdateView,
)

app_name = "authorization"


urlpatterns = [
    # Roles
    path(
        "roles/",
        RoleListView.as_view(),
        name="role-list",
    ),

    # Role permissions
    path(
        "roles/<str:public_id>/permissions/",
        RolePermissionsView.as_view(),
        name="role-permissions",
    ),

    path(
        "roles/<str:public_id>/permissions/update/",
        RolePermissionsUpdateView.as_view(),
        name="role-permissions-update",
    ),

    # Permission matrix
    path(
        "matrix/",
        PermissionMatrixView.as_view(),
        name="permission-matrix",
    ),
]