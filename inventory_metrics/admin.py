from django.contrib import admin
from inventory_metrics.models import (
    DailySystemMetrics,
    DailySecurityMetrics,
    DailyRoleMetrics,
    DailyDepartmentSnapshot,
    DailyLocationSnapshot, DailyLoginMetrics
)

@admin.register(DailySystemMetrics)
class DailySystemMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "total_users",
        "active_users_last_24h",
        "active_users_last_7d",
        "total_sessions",
        "active_sessions",
        "total_equipment",
        "total_components",
        "total_components_quantity",
    ]
    list_filter = ["date"]
    search_fields = ["date"]


@admin.register(DailySecurityMetrics)
class DailySecurityMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "password_resets",
        "active_password_resets",
        "expired_password_resets",
        "users_multiple_active_sessions",
        "users_with_revoked_sessions",
    ]
    list_filter = ["date"]
    search_fields = ["date"]


@admin.register(DailyRoleMetrics)
class DailyRoleMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "role",
        "total_users_with_role",
        "total_users_active_with_role",
    ]
    list_filter = ["date", "role"]
    search_fields = ["role"]


@admin.register(DailyDepartmentSnapshot)
class DailyDepartmentSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "snapshot_date",
        "department",
        "total_users",
        "total_admins",
        "total_locations",
        "total_rooms",
        "total_equipment",
        "total_components",
        "total_component_quantity",
    ]
    list_filter = ["snapshot_date", "department"]
    search_fields = ["department__name"]


@admin.register(DailyLocationSnapshot)
class DailyLocationSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "snapshot_date",
        "location",
        "total_users",
        "total_admins",
        "total_rooms",
        "total_equipment",
        "total_components",
        "total_component_quantity",
    ]
    list_filter = ["snapshot_date", "location"]
    search_fields = ["location__name"]

@admin.register(DailyLoginMetrics)
class DailyLoginMetricsAdmin(admin.ModelAdmin):
    list_display = ("date", "total_logins", "unique_users_logged_in", "failed_logins", "lockouts")
    list_filter = ("date",)
    ordering = ("-date",)