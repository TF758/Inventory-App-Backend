from django.contrib import admin
from .models import User, Department, UserLocation, Location, Equipment, Component, Consumable, Room

# Simple models
admin.site.register(User)
admin.site.register(Department)
admin.site.register(UserLocation)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'area', 'section', 'location')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'serial_number', 'public_id')  # visible in list
    readonly_fields = ('public_id',)  # visible in form, but cannot edit
    fields = ('name', 'brand', 'serial_number', 'model', 'public_id', 'location')


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
