from django.contrib import admin

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


from users.models.roles import RoleAssignment
from users.models.users import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    ordering = ("email",)

    list_display = (
        "email",
        "fname",
        "lname",
        "active_role",
        "public_id",
        "is_active",
        "is_locked",
        "failed_login_attempts",
        "locked_until",
        "created_by",
        "is_system_user",
        "force_password_change",
    )

    list_filter = (
        "is_active",
        "is_locked",
        "is_staff",
        "is_superuser",
        "is_system_user",
        "force_password_change",
    )

    search_fields = (
        "email",
        "fname",
        "lname",
        "public_id",
    )

    readonly_fields = (
        "public_id",
        "failed_login_attempts",
        "last_failed_login_at",
        "locked_until",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),

        (
            "Personal info",
            {
                "fields": (
                    "fname",
                    "lname",
                    "job_title",
                    "role",
                )
            },
        ),

        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),

        (
            "Security",
            {
                "fields": (
                    "is_locked",
                    "locked_reason",
                    "failed_login_attempts",
                    "last_failed_login_at",
                    "locked_until",
                    "force_password_change",
                )
            },
        ),

        (
            "System",
            {
                "fields": (
                    "public_id",
                    "created_by",
                    "is_system_user",
                )
            },
        ),

        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "fname",
                    "lname",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'location', 'room', 'assigned_by', 'assigned_date', 'public_id')
    readonly_fields = ('public_id',)
    search_fields = ('user__email', 'role', 'department__name', 'location__name', 'room__name', 'assigned_by__email')
    list_filter = ('role', 'department')