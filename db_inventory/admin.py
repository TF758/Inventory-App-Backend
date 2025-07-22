from django.contrib import admin

from .models import User, Department, UserLocation, Location, Equipment, Component, Consumable

admin.site.register(User)

admin.site.register(Department)

admin.site.register(UserLocation)

admin.site.register(Location)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'serial_number', 'identifier')  # shows in list view
    readonly_fields = ('identifier',)  # shows in form but read-only
    fields = ('name', 'brand', 'serial_number', 'model', 'identifier', 'location')  # 


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'model', 'identifier')
    readonly_fields = ('identifier',)
    fields = ('name', 'brand', 'quantity', 'serial_number', 'model', 'identifier', 'equipment')


admin.site.register(Consumable)
