from django.contrib import admin

from .models import (
    Permission,
    Role,
    RolePermission,
)


# =====================================================
# Role Permission Inline
# =====================================================

class RolePermissionInline(admin.TabularInline):
    model = RolePermission

    extra = 0

    autocomplete_fields = (
        "permission",
    )

    verbose_name = "Permission"

    verbose_name_plural = "Permissions"

    show_change_link = True

    # Future:
    # Once Permission Matrix UI is stable,
    # consider making system role permissions
    # read-only and managed exclusively through
    # the application.
    #
    # def has_add_permission(
    #     self,
    #     request,
    #     obj=None,
    # ):
    #     if obj and obj.is_system_role:
    #         return False
    #
    #     return True
    #
    # def has_delete_permission(
    #     self,
    #     request,
    #     obj=None,
    # ):
    #     if obj and obj.is_system_role:
    #         return False
    #
    #     return True


# =====================================================
# Permission Admin
# =====================================================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "module",
        "is_system",
    )

    list_filter = (
        "module",
        "is_system",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    ordering = (
        "module",
        "code",
    )

    list_per_page = 50

    save_on_top = True

    # Future:
    # Permissions should ideally be created
    # through migrations / seed data only.
    #
    # def has_add_permission(
    #     self,
    #     request,
    # ):
    #     return False
    #
    # def has_delete_permission(
    #     self,
    #     request,
    #     obj=None,
    # ):
    #     return False
    #
    # def get_readonly_fields(
    #     self,
    #     request,
    #     obj=None,
    # ):
    #     return (
    #         "code",
    #         "name",
    #         "description",
    #         "module",
    #         "is_system",
    #     )


# =====================================================
# Role Admin
# =====================================================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "scope_type",
        "level",
        "permission_count",
        "is_system_role",
    )

    list_filter = (
        "scope_type",
        "is_system_role",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "level",
    )

    list_per_page = 25

    save_on_top = True

    inlines = [
        RolePermissionInline,
    ]

    fieldsets = (
        (
            "Role Details",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                )
            },
        ),
        (
            "Authorization",
            {
                "fields": (
                    "scope_type",
                    "level",
                    "is_system_role",
                )
            },
        ),
    )

    def permission_count(self, obj):
        return obj.role_permissions.filter(
            enabled=True
        ).count()

    permission_count.short_description = (
        "Enabled Permissions"
    )

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):
        """
        Prevent accidental modification of
        system role metadata.
        """

        if obj and obj.is_system_role:

            return (
                "code",
                "scope_type",
                "level",
                "is_system_role",
            )

        return ()

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        """
        Prevent deleting system roles.
        """

        if obj and obj.is_system_role:
            return False

        return super().has_delete_permission(
            request,
            obj,
        )


# =====================================================
# Role Permission Admin
# =====================================================

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):

    list_display = (
        "role",
        "permission",
        "enabled",
        "updated_at",
    )

    list_filter = (
        "enabled",
        "role",
        "permission__module",
    )

    search_fields = (
        "role__code",
        "permission__code",
    )

    autocomplete_fields = (
        "role",
        "permission",
    )

    ordering = (
        "role__code",
        "permission__code",
    )

    list_per_page = 100

    save_on_top = True

    # Future:
    # Once the Permission Matrix UI is the
    # primary management surface, consider
    # making RolePermission read-only here.
    #
    # readonly_fields = (
    #     "role",
    #     "permission",
    #     "enabled",
    #     "updated_at",
    # )
    #
    # def has_add_permission(
    #     self,
    #     request,
    # ):
    #     return False
    #
    # def has_change_permission(
    #     self,
    #     request,
    #     obj=None,
    # ):
    #     return False
    #
    # def has_delete_permission(
    #     self,
    #     request,
    #     obj=None,
    # ):
    #     return False