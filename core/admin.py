from django.contrib import admin

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from core.security_policy import invalidate_security_policy_cache
from core.models.audit import AuditLog, SiteNameChangeHistory, SiteRelocationHistory
from core.models.base import PublicIDRegistry
from core.models.notifications import Notification
from core.models.security import PasswordResetEvent, SecuritySettings
from core.models.sessions import UserSession
from core.models.tasks import ScheduledTaskRun




@admin.register(SecuritySettings)
class SecuritySettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for runtime security policy configuration.
    Only one instance should exist.
    """

    list_display = (
        "session_idle_minutes",
        "session_absolute_hours",
        "max_concurrent_sessions",
        "lockout_attempts",
        "lockout_duration_minutes",
        "enable_account_lockout",
        "permanent_lock_threshold",
    )

    fieldsets = (
        (
            "Session Policy",
            {
                "fields": (
                    "session_idle_minutes",
                    "session_absolute_hours",
                    "max_concurrent_sessions",
                )
            },
        ),
       
        (
            "Account Security",
            {
                 "fields": (
                    "enable_account_lockout",
                    "lockout_attempts",
                    "lockout_duration_minutes",
                    "permanent_lock_threshold",
                    "reset_failed_attempts_after_minutes",
                )
            },
        ),
    )

    # -----------------------------------------------------
    # Enforce singleton
    # -----------------------------------------------------

    def has_add_permission(self, request):
        """
        Prevent creating more than one policy row.
        """
        if SecuritySettings.objects.exists():
            return False
        return super().has_add_permission(request)

    # -----------------------------------------------------
    # Cache invalidation
    # -----------------------------------------------------

    def save_model(self, request, obj, form, change):
        """
        Clear policy cache when settings are updated.
        """
        super().save_model(request, obj, form, change)
        invalidate_security_policy_cache()

    def delete_model(self, request, obj):
        """
        Clear policy cache if deleted.
        """
        super().delete_model(request, obj)
        invalidate_security_policy_cache()

    # -----------------------------------------------------
    # UI improvements
    # -----------------------------------------------------

    def has_delete_permission(self, request, obj=None):
        """
        Optional: prevent deletion to guarantee policy always exists.
        """
        return True

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "recipient",
        "type",
        "level",
        "entity_type",
        "entity_id",
        "is_read",
        "is_deleted",
        "created_at",
    )

    list_filter = (
        "type",
        "level",
        "is_read",
        "is_deleted",
        "created_at",
    )

    search_fields = (
        "public_id",
        "title",
        "message",
        "recipient__email",
        "recipient__username",
        "entity_id",
    )

    list_select_related = ("recipient",)

    ordering = ("-created_at", "-id")

    readonly_fields = (
        "public_id",
        "created_at",
        "read_at",
        "deleted_at",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("public_id", "recipient")
        }),
        ("Content", {
            "fields": ("type", "level", "title", "message")
        }),
        ("Entity Context", {
            "fields": ("entity_type", "entity_id", "meta"),
            "classes": ("collapse",),
        }),
        ("Status", {
            "fields": ("is_read", "read_at", "is_deleted", "deleted_at"),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )




@admin.register(PublicIDRegistry)
class PublicIDRegistryAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "model_label",
        "created_at",
    )

    search_fields = (
        "public_id",
        "model_label",
    )

    list_filter = (
        "model_label",
        "created_at",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "public_id",
        "model_label",
        "created_at",
    )

    # --------------------
    # Safety: make registry immutable in admin
    # --------------------

    def has_add_permission(self, request):
        return False  # IDs must only be created via code

    def has_change_permission(self, request, obj=None):
        return False  # prevent edits

    def has_delete_permission(self, request, obj=None):
        return False  # never allow deletion

@admin.register(ScheduledTaskRun)
class ScheduledTaskRunAdmin(admin.ModelAdmin):
    list_display = (
        "task_name",
        "status",
        "run_at",
        "duration_ms",
        "message",
    )

    list_filter = (
        "status",
        "task_name",
    )

    ordering = ("-run_at",)

    readonly_fields = (
        "task_name",
        "status",
        "run_at",
        "duration_ms",
        "schema_version",
        "message",
    )


admin.site.register(SiteNameChangeHistory)

admin.site.register(SiteRelocationHistory)




@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "absolute_expires_at", "created_at", "last_used_at", "ip_address")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "ip_address")

    ordering = ("-created_at",)  # "-" means descending order



@admin.register(PasswordResetEvent)
class PasswordResetEventAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'expires_at', 
        'used_at', 
        'created_at', 
        'is_valid_display'
    )
    list_filter = ('expires_at', 'used_at', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('token', 'created_at', 'used_at')
    ordering = ('-created_at',)

    def is_valid_display(self, obj):
        return obj.is_valid()
    is_valid_display.boolean = True
    is_valid_display.short_description = 'Valid'

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "user",
        "target_model",
        "target_name",
        "target_id",
        "department",
        "location",
        "room",
        "created_at",
    )

    list_filter = (
        "event_type",
        "department",
        "location",
        "room",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
        "target_model",
        "target_name",
        "target_id",
        "description",
        "metadata",
        "ip_address",
        "user_agent",
        "department_name",
        "location_name",
        "room_name",
    )

    readonly_fields = (
        # Core info
        'public_id',
        "event_type",
        "user",
        "created_at",

        # Target info
        "target_model",
        "target_id",
        "target_name",

        # Scope (FK + snapshot)
        "department",
        "department_name",
        "location",
        "location_name",
        "room",
        "room_name",

        # Technical info
        "description",
        "metadata",
        "ip_address",
        "user_agent",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Event Information", {
            "fields": ("public_id", "event_type", "created_at", "user_email", "user_public_id")
        }),
        ("Target Object", {
            "fields": (
                "target_model",
                "target_id",
                "target_name",
                "description",
                "metadata",
            )
        }),
        ("Scope (Location / Department)", {
            "fields": (
                "department", "department_name",
                "location", "location_name",
                "room", "room_name",
            )
        }),
        ("Technical Details", {
            "fields": ("ip_address", "user_agent")
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # Uncomment this ONLY during testing
    # def has_delete_permission(self, request, obj=None):
    #     return True  # or False to disable deletion completely

    # Optional: restrict visibility to department admins
    # Uncomment when ready to enforce scoping
    #
    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #
    #     if request.user.is_superuser:
    #         return qs
    #
    #     # If user has department attribute
    #     dept = getattr(request.user, "department", None)
    #     if dept:
    #         return qs.filter(department=dept)
    #
    #     # No department → restrict 

    # -----------------------------

# -----------------------------------------------------
# Agreement Inlines
# -----------------------------------------------------
