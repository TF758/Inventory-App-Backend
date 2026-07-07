from django.contrib import admin

from .models import Permission, RolePermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "domain",
        "name",
        "scope_type",
    )

    list_filter = (
        "domain",
        "scope_type",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    ordering = (
        "domain",
        "code",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Permission",
            {
                "fields": (
                    "domain",
                    "code",
                    "name",
                    "scope_type",
                    "description",
                )
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "permission",
        "permission_domain",
    )

    list_filter = (
        "role",
        "permission__domain",
    )

    search_fields = (
        "role",
        "permission__code",
        "permission__name",
    )

    autocomplete_fields = (
        "permission",
    )

    ordering = (
        "role",
        "permission__domain",
        "permission__code",
    )

    def permission_domain(self, obj):
        return obj.permission.domain

    permission_domain.short_description = "Domain"