from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import RoleAssignment, Location, Department, Room, User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["public_id"] = str(user.public_id)
        token["fname"] = user.fname
        token["lname"] = user.lname
        token["active_role_id"] = (
            user.active_role.id if user.active_role else None
        )

        if "user_id" in token:
            del token["user_id"]

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        active_role_data = None
        if self.user.active_role:
            active_role_data = RoleReadSerializer(self.user.active_role).data

        data.update({
            "public_id": str(self.user.public_id),
            "fname": self.user.fname,
            "lname": self.user.lname,
            "active_role_id": (
                self.user.active_role.id if self.user.active_role else None
            ),
            "active_role": active_role_data,
        })

        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_message = {
        'bad_token': ('Token is expired or invalid')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise serializers.ValidationError(
                {'refresh': self.error_messages['bad_token']}
            )
        

class RoleListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
 
    class Meta:
        model = RoleAssignment
        fields = [ 'id', 'role', 'department_name', 'location_name', 'room_name', 'assigned_by', 'assigned_date']


class RoleReadSerializer(serializers.ModelSerializer):
    area_id = serializers.SerializerMethodField()
    area_type = serializers.SerializerMethodField()
    area_name = serializers.SerializerMethodField()
    assigned_by = serializers.CharField(source="assigned_by.username", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "role",
            "area_id",       # <-- generic id (public_id of dept/location/room)
            "area_type",     # <-- tells you which one it is
            "area_name",     # <-- display name
            "assigned_by",
            "assigned_date",
        ]

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
    


class RoleWriteSerializer(serializers.ModelSerializer):
    # Optionally show related names for read-only
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
        """
        Reuse your model clean logic to enforce scope restrictions.
        """
        # This allows the model clean() to raise ValidationErrors
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