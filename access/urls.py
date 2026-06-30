from django.urls import path

from access.views import PermissionMatrixView



urlpatterns = [
    path(
        "permissions/matrix/",
        PermissionMatrixView.as_view(),
        name="permission-matrix",
    ),
]