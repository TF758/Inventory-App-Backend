from django.urls import path

from authorization.api.views import PermissionMatrixView, RolePermissionManagementView

urlpatterns = [

    # ==========================================
    # Permission Matrix
    # ==========================================

    path(
        "permission-matrix/",
        PermissionMatrixView.as_view(),
        name="permission-matrix",
    ),

    # ==========================================
    # Role Permission Management
    # ==========================================

    path(
        "roles/<str:public_id>/permissions/",
        RolePermissionManagementView.as_view(),
        name="role-permissions",
    ),
]