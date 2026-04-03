from django.contrib import admin
from db_inventory.models.site import *
from db_inventory.models.base import *
from db_inventory.models.assets import *
from db_inventory.models.users import *
from db_inventory.models.security import *
from db_inventory.models.roles import *
from db_inventory.models.audit import *
from db_inventory.models.asset_assignment import *
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.admin import GenericTabularInline
from db_inventory.security_policy import invalidate_security_policy_cache

# Simple models


class ReturnRequestItemInline(admin.TabularInline):
    model = ReturnRequestItem
    extra = 0
    readonly_fields = ("item_type", "quantity", "status")


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "requester",
        "status",
        "requested_at",
        "processed_at",
    )

    list_filter = (
        "status",
        "requested_at",
    )

    search_fields = (
        "id",
        "requester__email",
        "requester__username",
    )

    readonly_fields = (
        "requested_at",
        "processed_at",
    )

    inlines = [ReturnRequestItemInline]


@admin.register(ReturnRequestItem)
class ReturnRequestItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "return_request",
        "item_type",
        "quantity",
        "status",
    )

    list_filter = (
        "status",
        "item_type",
    )

    search_fields = (
        "return_request__id",
    )

    readonly_fields = (
        "return_request",
    )

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
                    "lockout_attempts",
                    "lockout_duration_minutes",
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

admin.site.register(EquipmentAssignment)

admin.site.register(EquipmentEvent)

admin.site.register(SiteNameChangeHistory)

admin.site.register(SiteRelocationHistory)

admin.site.register(Department)

@admin.register(UserPlacement)
class UserPlacementAdmin(admin.ModelAdmin):
    list_display = ("public_id", "user_full_name", "user_public_id", "room_public_id", "date_joined")
    search_fields = (
        "user__fname",
        "user__lname",
        "user__public_id",
        "room__public_id",
    )


    def user_full_name(self, obj):
        return f"{obj.user.fname} {obj.user.lname}"
    user_full_name.short_description = "User Name"

    def user_public_id(self, obj):
        return obj.user.public_id
    user_public_id.short_description = "User Public ID"

    def room_public_id(self, obj):
        return obj.room.public_id if obj.room else "-"
    room_public_id.short_description = "Room Public ID"
    
@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ("public_id", "name", "quantity", "room", "is_deleted", "deleted_at")
    search_fields = ("public_id", "name")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "absolute_expires_at", "created_at", "last_used_at", "ip_address")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "ip_address")

    ordering = ("-created_at",)  # "-" means descending order

@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'location', 'room', 'assigned_by', 'assigned_date', 'public_id')
    readonly_fields = ('public_id',)
    search_fields = ('user__email', 'role', 'department__name', 'location__name', 'room__name', 'assigned_by__email')
    list_filter = ('role', 'department')

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "fname", "lname","active_role", "public_id", "is_active",'is_locked', "created_by","is_system_user", "force_password_change" )
    search_fields = ("email", "fname", "lname", "public_id")
    readonly_fields = ("public_id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("fname", "lname", "job_title", "role")}),
        ("Permissions", {"fields": ("is_active", 'is_locked', "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "fname", "lname", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    readonly_fields = ("public_id",)
    search_fields = ('name', 'location__name', 'public_id')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'serial_number', 'public_id')  
    readonly_fields = ('public_id',) 
    search_fields = (
        "public_id",
        "name",
        "brand",
        "model",
    )
    fields = ('name', 'brand', 'serial_number', 'model', 'public_id', 'room', 'status', 'is_deleted', 'deleted_at')


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'model', 'public_id')
    readonly_fields = ('public_id',)
    fields = ('name', 'brand', 'quantity', 'serial_number', 'model', 'public_id', 'equipment')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'public_id')  # adjust based on your model fields
    readonly_fields = ('public_id',)
    fields = ('name', 'department', 'public_id') 


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ('name',  'quantity', 'public_id')  # adjust fields as per model
    readonly_fields = ('public_id',)
    search_fields = ( "public_id", "name", )
    fields = ('name','quantity', 'description', 'public_id')


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
# Agreement Items Inline
# -----------------------------

class AssetAgreementItemInline(admin.TabularInline):

    model = AssetAgreementItem
    extra = 1

    autocomplete_fields = [
        "equipment",
        "consumable",
        "accessory",
    ]

    fields = (
        "equipment",
        "consumable",
        "accessory",
        "quantity",
    )


# -----------------------------
# Agreement Admin
# -----------------------------

@admin.register(AssetAgreement)
class AssetAgreementAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "name",
        "agreement_type",
        "vendor",
        "expiry_date",
        "department",
        "location",
        "room",
    )

    list_filter = (
        "agreement_type",
      
    )

    search_fields = (
        "public_id",
        "name",
        "vendor",
        "reference_number",
    )

    readonly_fields = (
        "public_id",
    )

    inlines = [
        AssetAgreementItemInline
    ]

    ordering = ("-start_date",)