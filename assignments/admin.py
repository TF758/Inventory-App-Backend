from django.contrib import admin

from assignments.models.asset_assignment import AccessoryEvent, ConsumableEvent, EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem

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

admin.site.register(EquipmentAssignment)

admin.site.register(EquipmentEvent)



# -----------------------------------------------------
# Accessory Events
# -----------------------------------------------------


@admin.register(AccessoryEvent)
class AccessoryEventAdmin(admin.ModelAdmin):

    list_display = (
        "accessory",
        "event_type",
        "user",
        "quantity",
        "quantity_change",
        "occurred_at",
        "reported_by",
    )

    list_filter = (
        "event_type",
        "occurred_at",
    )

    search_fields = (
        "accessory__name",
        "accessory__public_id",
        "user__email",
        "reported_by__email",
        "notes",
    )

    readonly_fields = (
        "accessory",
        "user",
        "quantity",
        "quantity_change",
        "event_type",
        "occurred_at",
        "reported_by",
        "notes",
    )

    ordering = (
        "-occurred_at",
    )

    date_hierarchy = "occurred_at"


# -----------------------------------------------------
# Consumable Events
# -----------------------------------------------------


@admin.register(ConsumableEvent)
class ConsumableEventAdmin(admin.ModelAdmin):

    list_display = (
        "consumable",
        "event_type",
        "user",
        "quantity",
        "quantity_change",
        "occurred_at",
        "reported_by",
    )

    list_filter = (
        "event_type",
        "occurred_at",
    )

    search_fields = (
        "consumable__name",
        "consumable__public_id",
        "user__email",
        "reported_by__email",
        "notes",
    )

    readonly_fields = (
        "consumable",
        "issue",
        "user",
        "quantity",
        "quantity_change",
        "event_type",
        "occurred_at",
        "reported_by",
        "notes",
    )

    ordering = (
        "-occurred_at",
    )

    date_hierarchy = "occurred_at"

