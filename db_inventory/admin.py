from django.contrib import admin
from db_inventory.models.site import *
from db_inventory.models.assets import *
from db_inventory.models.users import *
from db_inventory.models.security import *
from db_inventory.models.roles import *
from db_inventory.models.audit import *
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

# Simple models

admin.site.register(SiteNameChangeHistory)

admin.site.register(SiteRelocationHistory)

admin.site.register(Department)

@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
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
admin.site.register(Accessory)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "last_used_at", "ip_address")
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
    fields = ('name', 'brand', 'serial_number', 'model', 'public_id', 'room')


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
        "user",
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

