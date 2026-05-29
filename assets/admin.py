from django.contrib import admin

from assets.models.assets import Accessory, Component, Consumable, Equipment



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


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ("public_id", "name", "quantity", "room", "is_deleted", "deleted_at")
    search_fields = ("public_id", "name")


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ('name',  'quantity', 'public_id')  # adjust fields as per model
    readonly_fields = ('public_id',)
    search_fields = ( "public_id", "name", )
    fields = ('name','quantity', 'description', 'public_id')



