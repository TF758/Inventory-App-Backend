from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import RoleAssignment, Location, Department, Room, User



class ActiveRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["active_role"]

    def validate_active_role(self, value):
        # Ensure the role assignment belongs to this user
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Cannot select a role that isn't yours.")
        return value



class RoleListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
 
    class Meta:
        model = RoleAssignment
        fields = [ 'id', 'role', 'department_name', 'location_name', 'room_name', 'assigned_by', 'assigned_date']


class UserRoleReadSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)
    assigned_by = serializers.CharField(source="assigned_by.username", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "role",
            "department_name",
            "location_name",
            "room_name",
            "assigned_by",
            "assigned_date",
        ]

class RoleSwitchSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()

    def validate_role_id(self, value):
        """
        Ensure the role exists and belongs to the current user.
        """
        user = self.context['request'].user
        try:
            role = RoleAssignment.objects.get(id=value, user=user)
        except RoleAssignment.DoesNotExist:
            raise serializers.ValidationError("This role does not belong to the current user or does not exist.")

        return role  # return the RoleAssignment instance for convenience
    

class UserRoleWriteSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user",
            "user_email",
            "role",
            "department",
            "department_name",
            "location",
            "location_name",
            "room",
            "room_name",
            "assigned_by",
            "assigned_date",
        ]
        read_only_fields = ["assigned_date", "assigned_by"]

    def validate(self, attrs):
        instance = RoleAssignment(**attrs)
        instance.clean()
        return attrs

    def create(self, validated_data):
        # Automatically assign the current user as `assigned_by` if request available
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["assigned_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Optionally update assigned_by on update
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["assigned_by"] = request.user
        return super().update(instance, validated_data)