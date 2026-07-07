from django.contrib import admin
from sites.models.sites import Department, Location, Room, UserPlacement

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "public_id",
        "location_count",
        "room_count",
    )

    search_fields = (
        "name",
        "public_id",
        "description",
    )

    readonly_fields = (
        "public_id",
    )

    fields = (
        "name",
        "description",
        "img_link",
        "public_id",
    )

    def location_count(self, obj):
        return obj.locations.count()

    location_count.short_description = "Locations"

    def room_count(self, obj):
        return Room.objects.filter(
            location__department=obj
        ).count()

    room_count.short_description = "Rooms"

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'public_id')  # adjust based on your model fields
    readonly_fields = ('public_id',)
    fields = ('name', 'department', 'public_id') 


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    readonly_fields = ("public_id",)
    search_fields = ('name', 'location__name', 'public_id')

@admin.register(UserPlacement)
class UserPlacementAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "user_full_name",
        "user_public_id",
        "department_name",
        "location_name",
        "room_name",
        "is_current",
        "date_joined",
    )

    list_filter = (
        "is_current",
        "room__location__department",
        "room__location",
    )

    search_fields = (
        "public_id",

        "user__public_id",
        "user__email",
        "user__fname",
        "user__lname",

        "room__public_id",
        "room__name",

        "room__location__name",
        "room__location__department__name",
    )

    autocomplete_fields = (
        "user",
        "room",
    )

    list_select_related = (
        "user",
        "room",
        "room__location",
        "room__location__department",
    )

    ordering = (
        "-is_current",
        "-date_joined",
    )

    def user_full_name(self, obj):
        return f"{obj.user.fname} {obj.user.lname}"

    user_full_name.short_description = "User"

    def user_public_id(self, obj):
        return obj.user.public_id

    user_public_id.short_description = "User ID"

    def department_name(self, obj):
        if (
            obj.room
            and obj.room.location
            and obj.room.location.department
        ):
            return obj.room.location.department.name

        return "-"

    department_name.short_description = "Department"

    def location_name(self, obj):
        if obj.room and obj.room.location:
            return obj.room.location.name

        return "-"

    location_name.short_description = "Location"

    def room_name(self, obj):
        return obj.room.name if obj.room else "-"

    room_name.short_description = "Room"