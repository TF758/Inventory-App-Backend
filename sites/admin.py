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