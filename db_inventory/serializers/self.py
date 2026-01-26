
from db_inventory.models.users import User
from rest_framework import serializers


class SelfUserProfileSerializer(serializers.ModelSerializer):
    equipment_count = serializers.IntegerField(read_only=True)
    accessory_count = serializers.IntegerField(read_only=True)
    consumable_count = serializers.IntegerField(read_only=True)

    current_location = serializers.SerializerMethodField()
    active_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "public_id",
            "email",
            "fname",
            "lname",
            "job_title",
            "is_active",
            "last_login",
            "current_location",
            "active_role",
            "equipment_count",
            "accessory_count",
            "consumable_count",
        )

    def get_current_location(self, obj):
        ul = (
            obj.user_locations
            .select_related("room__location__department")
            .filter(is_current=True)
            .first()
        )

        if not ul or not ul.room:
            return None

        return {
            "room": ul.room.name,
            "location": ul.room.location.name,
            "department": ul.room.location.department.name,
        }

    def get_active_role(self, obj):
        role = obj.active_role
        if not role:
            return None

        if role.role == "SITE_ADMIN":
            return {
                "role": role.role,
                "scope_type": "site",
                "scope_name": "Entire Site",
            }

        if role.room:
            return {
                "role": role.role,
                "scope_type": "room",
                "scope_name": role.room.name,
            }

        if role.location:
            return {
                "role": role.role,
                "scope_type": "location",
                "scope_name": role.location.name,
            }

        if role.department:
            return {
                "role": role.role,
                "scope_type": "department",
                "scope_name": role.department.name,
            }

        return {
            "role": role.role,
            "scope_type": None,
            "scope_name": None,
        }


class SelfAssignedEquipmentSerializer(serializers.Serializer):
    """
    Serializer for equipment currently assigned to the authenticated user.
    Input model: EquipmentAssignment
    Output: flattened equipment data
    """

    public_id = serializers.CharField(source="equipment.public_id")
    name = serializers.CharField(source="equipment.name")
    brand = serializers.CharField(source="equipment.brand")
    model = serializers.CharField(source="equipment.model")
    status = serializers.CharField(source="equipment.status")

    room = serializers.SerializerMethodField()

    def get_room(self, obj):
        room = obj.equipment.room
        if not room:
            return None

        return {
            "public_id": room.public_id,
            "name": room.name,
        }