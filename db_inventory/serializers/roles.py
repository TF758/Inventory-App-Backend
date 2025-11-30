from rest_framework import serializers
from ..models import RoleAssignment, Location, Department, Room, User
from db_inventory.permissions.helpers import ensure_permission
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from db_inventory.models import RoleAssignment
from rest_framework.exceptions import PermissionDenied, ValidationError


class ActiveRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["active_role"]
        read_only_fields = ["active_role"]

    def validate_active_role(self, value):
        # Ensure the role assignment belongs to this user
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Cannot activate this role.")
        return value


class RoleReadSerializer(serializers.ModelSerializer):

    """Returns A user's Role and area (department/location/room)"""
    area_id = serializers.SerializerMethodField()
    area_type = serializers.SerializerMethodField()
    area_name = serializers.SerializerMethodField()
    assigned_by = serializers.CharField(source="assigned_by.username", read_only=True)
    user_public_id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    


    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "role",
            "user_public_id",
            "username",
            "public_id",
            "area_id",       # <-- generic id (public_id of dept/location/room)
            "area_type",     # <-- tells you which one it is
            "area_name",     # <-- display name
            "assigned_by",
            "assigned_date",
        ]

        read_only_fields = ["area_id", "area_type", "area_name", "public_id"]

    def get_area_id(self, obj):
        if obj.department:
            return obj.department.public_id
        if obj.location:
            return obj.location.public_id
        if obj.room:
            return obj.room.public_id
        return None

    def get_area_type(self, obj):
        if obj.department:
            return "department"
        if obj.location:
            return "location"
        if obj.room:
            return "room"
        return None

    def get_area_name(self, obj):
        if obj.department:
            return obj.department.name
        if obj.location:
            return obj.location.name
        if obj.room:
            return obj.room.name
        return "N/A"
    
    def get_user_public_id(self, obj):
        return obj.user.public_id if obj.user else None

    def get_username(self, obj):
        user = obj.user
        if not user:
            return "N/A"
        if user.fname and user.lname:
            return f"{user.fname} {user.lname}"
        return user.email or "N/A"

class RoleWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating RoleAssignment.
    Accepts public_id for user, department, location, room.
    """
    user = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=User.objects.all()
    )

    department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    location = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    room = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    class Meta:
        model = RoleAssignment
        fields = [
            "user",
            "role",
            "department",
            "location",
            "room",
            "assigned_by",
            "assigned_date",
        ]
        read_only_fields = ["assigned_by", "assigned_date"]

    # --- Field-level validation ---
    def validate_user(self, value):
        if isinstance(value, str):
            try:
                value = User.objects.get(public_id=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found.")
        return value

    def validate_department(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = Department.objects.get(public_id=value)
            except Department.DoesNotExist:
                raise serializers.ValidationError("Department not found.")
        return value

    def validate_location(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = Location.objects.get(public_id=value)
            except Location.DoesNotExist:
                raise serializers.ValidationError("Location not found.")
        return value

    def validate_room(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = Room.objects.get(public_id=value)
            except Room.DoesNotExist:
                raise serializers.ValidationError("Room not found.")
        return value

    # --- Global validation ---
    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        # --- Extract role string safely ---
        role_data = attrs.get("role") or request.data.get("role")

        if isinstance(role_data, dict):
            role = role_data.get("role")
        else:
            role = role_data

        if role is None:
            if self.instance:
                role = self.instance.role
            else:
                raise serializers.ValidationError("Role must be provided.")

        # --- Resolve scope fields ---
        room = attrs.get("room")
        location = attrs.get("location")
        department = attrs.get("department")

        # --- Target user (handles POST + PATCH) ---
        target_user = attrs.get("user") or getattr(self.instance, "user", None)

        # --- Active role of the acting user ---
        active_role = getattr(user, "active_role", None)

        # Auto-assign department for dept-admin assigning dept roles
        if role.startswith("DEPARTMENT_") and not department and active_role and active_role.department:
            department = active_role.department

        # --- DEPARTMENT_ADMIN assigning ROOM roles ---
        if (user and active_role and active_role.role == "DEPARTMENT_ADMIN" and role.startswith("ROOM_")):
            if room and room.location.department != active_role.department:
                raise PermissionDenied("Cannot assign ROOM role outside your department")
            department = None  # clearing department for room role

        # --- LOCATION_ADMIN assigning ROOM roles ---
        if (user and active_role and active_role.role == "LOCATION_ADMIN" and role.startswith("ROOM_")):

            # Room must belong to their location
            if room and room.location != active_role.location:
                raise PermissionDenied("Cannot assign ROOM role outside your location")

            # Prevent location-moving
            if location and location != active_role.location:
                raise PermissionDenied("Cannot change location outside your scope")

            location = None  # clearing location for room role

        # Auto-assign location for location roles
        if role.startswith("LOCATION_") and not location and active_role and active_role.location:
            location = active_role.location

        # Auto-assign room for room roles
        if role.startswith("ROOM_") and not room and active_role and active_role.room:
            room = active_role.room

        # --- Run permission engine ---
        ensure_permission(
            user,
            role,
            room=room,
            location=location,
            department=department,
        )

        # Update attrs
        attrs.update({
            "room": room,
            "location": location,
            "department": department,
        })

        # --- Validate model-level clean() ---
        try:
            temp = RoleAssignment(**attrs)
            temp.clean()
        except DjangoValidationError as e:
            msg = (
                getattr(e, "message_dict", None)
                or getattr(e, "messages", None)
                or str(e)
            )
            raise serializers.ValidationError(msg)

        # --- Prevent duplicates ---
        existing = RoleAssignment.objects.filter(
            user=target_user,
            role=role,
            room=room,
            location=location,
            department=department,
        )
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError("User already has this role in the specified scope.")

        return attrs
    # --- Create / Update ---
    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["assigned_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["assigned_by"] = request.user
        return super().update(instance, validated_data)
