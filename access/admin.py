from django.contrib import admin

from .models import (
    Permission,
    RolePermission,
)


admin.site.register(Permission)
admin.site.register(RolePermission)