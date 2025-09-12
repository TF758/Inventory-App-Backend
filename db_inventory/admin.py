from django.contrib import admin
from .models import User, Department, UserLocation, Location, Equipment, Component, Consumable, Room, RoleAssignment
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

# Simple models

admin.site.register(Department)
admin.site.register(UserLocation)

admin.site.register(RoleAssignment)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "fname", "lname","active_role", "is_staff", "is_active")
    search_fields = ("email", "fname", "lname")
    readonly_fields = ("public_id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("fname", "lname", "job_title", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
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
    list_display = ('name', 'area', 'section', 'location')
    readonly_fields = ("public_id",)


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
    fields = ('name','quantity', 'serial_number', 'public_id')
