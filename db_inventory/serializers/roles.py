from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import RoleAssignment, Location, Department, Room, User



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
          default=None      # 
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
        user = attrs.get("user")
        role = attrs.get("role")
        department = attrs.get("department")
        location = attrs.get("location")
        room = attrs.get("room")

     
        existing = RoleAssignment.objects.filter(
            user=user,
            role=role,
            department=department,
            location=location,
            room=room,
        ).exists()

        if existing:
            raise serializers.ValidationError({
                "detail": f"User already has the '{role}' role assigned for this context."
            })

        # Allow model-level clean() to enforce rules
        instance = RoleAssignment(**attrs)
        instance.clean()
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
