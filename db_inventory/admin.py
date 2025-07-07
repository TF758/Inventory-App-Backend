from django.contrib import admin

from .models import User, Department, UserDepartment, Location, Equipment, Component, Consumable

admin.site.register(User)

admin.site.register(Department)

admin.site.register(UserDepartment)

admin.site.register(Location)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'serial_number', 'identifier')  # shows in list view
    readonly_fields = ('identifier',)  # shows in form but read-only
    fields = ('name', 'brand', 'serial_number', 'model', 'identifier', 'department', 'location')  # 


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'model', 'identifier')
    readonly_fields = ('identifier',)
    fields = ('name', 'brand', 'serial_number', 'model', 'identifier', 'equipment')


admin.site.register(Consumable)
