from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import RoleAssignment, Location, Department, Room, User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Always include basic user info
        token["public_id"] = str(user.public_id)
        token["fname"] = user.fname
        token["lname"] = user.lname

        token["active_role_id"] = user.active_role.id if user.active_role else None


        if "user_id" in token:
            del token["user_id"]


        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user info into response
        data.update({
            "public_id": str(self.user.public_id),
            "fname": self.user.fname,
            "lname": self.user.lname,
            "active_role_id": self.user.active_role.id if self.user.active_role else None
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
    user_id = serializers.SlugRelatedField(
        slug_field='public_id',
        queryset=User.objects.all(),
        source='user'
    )
    department = serializers.SlugRelatedField(
        slug_field='public_id',
        queryset=Department.objects.all(),
        allow_null=True,
        required=False
    )
    location = serializers.SlugRelatedField(
        slug_field='public_id',
        queryset=Location.objects.all(),
        allow_null=True,
        required=False
    )
    room = serializers.SlugRelatedField(
        slug_field='public_id',
        queryset=Room.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = RoleAssignment
        fields = [
            'user_id', 'role', 'department', 'location', 'room'
        ]
