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

        if "user_id" in token:
            del token["user_id"]


        # Handle active role logic
        roles = list(user.role_assignments.all())
        if len(roles) == 1:
            token["active_role_id"] = roles[0].id
        else:
            token["active_role_id"] = None

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user info into response
        data.update({
            "public_id": str(self.user.public_id),
            "fname": self.user.fname,
            "lname": self.user.lname,
        })
        

        # Active role logic
        roles = list(self.user.role_assignments.all())
        if len(roles) == 1:
            active_role = roles[0]
            data["active_role_id"] = active_role.id
        else:
            active_role = None
            data["active_role_id"] = None

        # Return all role assignments so frontend can choose
        data["roles"] = [
            {
                "id": r.id,
                "role": r.role,
                "department": r.department_id,
                "location": r.location_id,
                "room": r.room_id,
            }
            for r in roles
        ]

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
 

    class Meta:
        model = RoleAssignment
        fields = [ 'id', 'role', 'department', 'location', 'room']


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
    

class UserRoleReadSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.public_id', read_only=True)
    user_fname = serializers.CharField(source='user.fname', read_only=True)
    user_lname = serializers.CharField(source='user.lname', read_only=True)
    department = serializers.CharField(source='department.public_id', read_only=True)
    location = serializers.CharField(source='location.public_id', read_only=True)
    room = serializers.CharField(source='room.public_id', read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            'user_id', 'user_fname', 'user_lname',
            'role', 'department', 'location', 'room'
        ]

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
