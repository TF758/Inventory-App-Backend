from rest_framework import serializers
from users.models.users import User
from sites.models.sites import Room, UserPlacement
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue

class UserReadSerializerFull(serializers.ModelSerializer):

    current_role = serializers.CharField(
        source="active_role.get_role_id",
        read_only=True,
    )

    is_actually_locked = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "public_id",

            "email",
            "fname",
            "lname",

            "job_title",

            "last_login",

            "is_active",
            "is_locked",

            "is_actually_locked",

            "failed_login_attempts",
            "locked_until",
            "locked_reason",

            "current_role",

            "force_password_change",
        ]

        read_only_fields = (
            "public_id",
            "last_login",
            "is_actually_locked",
            "failed_login_attempts",
            "locked_until",
            "locked_reason",
        )

    def get_is_actually_locked(self, obj):

        return (
            obj.is_locked
            or (
                obj.locked_until is not None
                and obj.locked_until > timezone.now()
            )
        )


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,  
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(  
        write_only=True,
        required=False,
        allow_blank=True, 
        style={'input_type': 'password'}
    )


    class Meta:
        model = User
        fields = [
            'email', 'fname', 'lname', 'job_title', 'is_active',   'password',
            'confirm_password',  
        ]

    def validate(self, attrs):
        """
        Ensure password and confirm_password match if password is provided.
        """
        password = attrs.get('password')
        confirm_password = attrs.pop('confirm_password', None)

        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError({
                "confirm_password": "Password fields do not match." #nosec
            })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        """
        Update user fields. Password updates are handled separately.
        """
        validated_data.pop('password', None)
        validated_data.pop('confirm_password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class UserAreaSerializer(serializers.ModelSerializer):

    """Provide information about a user and thier location"""
    user_id = serializers.CharField(source='user.public_id')
    email = serializers.EmailField(source='user.email')
    fname = serializers.CharField(source='user.fname')
    lname = serializers.CharField(source='user.lname')

    is_active = serializers.BooleanField(source='user.is_active')
    is_locked = serializers.BooleanField(source='user.is_locked')
    

    room_id = serializers.CharField(source='room.public_id')
    room_name = serializers.CharField(source='room.name')

    location_id = serializers.CharField(source='room.location.public_id')
    location_name = serializers.CharField(source='room.location.name')

    department_id = serializers.CharField(source='room.location.department.public_id')
    department_name = serializers.CharField(source='room.location.department.name')

    class Meta:
        model = UserPlacement
        fields = [
            'public_id',
            'user_id', 'email', 'fname', 'lname', 'is_current', 'is_active', 'is_locked',
            'room_id', 'room_name',
            'location_id', 'location_name',
            'department_id', 'department_name',
        ]
        read_only_fields = fields

    def __init__(self, *args, **kwargs):
        exclude_room = kwargs.pop('exclude_room', False)
        exclude_location = kwargs.pop('exclude_location', False)
        exclude_department = kwargs.pop('exclude_department', False)
        super().__init__(*args, **kwargs)


        if exclude_room:
            self.fields.pop('room_id', None)
            self.fields.pop('room_name', None)
        if exclude_location:
            self.fields.pop('location_id', None)
            self.fields.pop('location_name', None)
        if exclude_department:
            self.fields.pop('department_id', None)
            self.fields.pop('department_name', None)


class UserPlacementWriteSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(write_only=True)
    room_id = serializers.CharField(write_only=True, allow_null=True, required=False)

    public_id = serializers.CharField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = UserPlacement
        fields = ['public_id', 'user_id', 'room_id', 'date_joined']

    def validate(self, attrs):
        user_id = attrs.get("user_id")

        # Resolve user
        if self.instance:
            user = self.instance.user
        else:
            if not user_id:
                raise serializers.ValidationError(
                    {"user_id": "This field is required."}
                )
            try:
                user = User.objects.only("id").get(public_id=user_id)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"user_id": "Invalid user public_id."}
                )

        # Resolve room
        room_id = attrs.get("room_id")
        room = None

        if room_id is not None:
            try:
                room = Room.objects.only("id").get(public_id=room_id)
            except Room.DoesNotExist:
                raise serializers.ValidationError(
                    {"room_id": "Invalid room public_id."}
                )
        elif self.instance:
            room = self.instance.room

        attrs["user"] = user
        attrs["room"] = room

        return attrs

    def create(self, validated_data):
        validated_data.pop('user_id', None)
        validated_data.pop('room_id', None)

        user = validated_data['user']

        with transaction.atomic():
            # Clear previous current
            UserPlacement.objects.filter(
                user=user,
                is_current=True
            ).update(is_current=False)

            # Create new current
            return UserPlacement.objects.create(
                **validated_data,
                is_current=True,
                date_joined=timezone.now()
            )
        
    def update(self, instance, validated_data):
        validated_data.pop('user_id', None)
        validated_data.pop('room_id', None)
        return super().update(instance, validated_data)

class UserTransferSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    room_id  = serializers.CharField()

    def validate(self, attrs):
        try:
            user = User.objects.get(public_id=attrs['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "Invalid user public_id."})

        try:
            room = Room.objects.get(public_id=attrs['room_id'])
        except Room.DoesNotExist:
            raise serializers.ValidationError({"room_id": "Invalid room public_id."})

        attrs['user'] = user
        attrs['room'] = room
        return attrs
    
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    equipment_count = serializers.IntegerField(read_only=True)
    accessory_count = serializers.IntegerField(read_only=True)
    consumable_count = serializers.IntegerField(read_only=True)
    current_role = serializers.SerializerMethodField()


    class Meta:
        model = User
        fields = (
            "public_id",
            "email",
            "fname",
            "lname",
            "job_title",
            "current_role",
            'last_login',
            'is_active',
            "equipment_count",
            "accessory_count",
            "consumable_count",
        )
    def get_current_role(self, obj):
        return obj.get_active_role_public_id()
    
class UserAccessoryAssignmentSerializer(serializers.ModelSerializer):
    public_id = serializers.CharField(source="accessory.public_id", read_only=True)
    name = serializers.CharField(source="accessory.name", read_only=True)
    serial_number = serializers.CharField(source="accessory.serial_number", read_only=True)

    room_id = serializers.CharField(source="accessory.room.public_id", read_only=True)
    room_name = serializers.CharField(source="accessory.room.name", read_only=True)

    location_id = serializers.CharField(
        source="accessory.room.location.public_id",
        read_only=True
    )
    location_name = serializers.CharField(
        source="accessory.room.location.name",
        read_only=True
    )

    department_id = serializers.CharField(
        source="accessory.room.location.department.public_id",
        read_only=True
    )
    department_name = serializers.CharField(
        source="accessory.room.location.department.name",
        read_only=True
    )

    assigned_by_id = serializers.CharField(
        source="assigned_by.public_id",
        read_only=True
    )

    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AccessoryAssignment
        fields = [
            "public_id",
            "name",
            "serial_number",
            "quantity",          # quantity held by user
            "assigned_at",
            "assigned_by_id",
            "assigned_by_name",
            "room_id",
            "room_name",
            "location_id",
            "location_name",
            "department_id",
            "department_name",
        ]

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return f"{obj.assigned_by.fname} {obj.assigned_by.lname}"
        return None
    
    
class UserConsumableIssueSerializer(serializers.ModelSerializer):
    public_id = serializers.CharField(source="consumable.public_id", read_only=True)
    name = serializers.CharField(source="consumable.name", read_only=True)
    description = serializers.CharField(source="consumable.description", read_only=True)

    room_id = serializers.CharField(source="consumable.room.public_id", read_only=True)
    room_name = serializers.CharField(source="consumable.room.name", read_only=True)

    location_id = serializers.CharField(
        source="consumable.room.location.public_id",
        read_only=True
    )
    location_name = serializers.CharField(
        source="consumable.room.location.name",
        read_only=True
    )

    department_id = serializers.CharField(
        source="consumable.room.location.department.public_id",
        read_only=True
    )
    department_name = serializers.CharField(
        source="consumable.room.location.department.name",
        read_only=True
    )

    assigned_by_id = serializers.CharField(
        source="assigned_by.public_id",
        read_only=True
    )

    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ConsumableIssue
        fields = [
            "public_id",
            "name",
            "description",
            "quantity",          # remaining quantity
            "issued_quantity",   # original issued
            "purpose",
            "assigned_at",
            "assigned_by_id",
            "assigned_by_name",
            "room_id",
            "room_name",
            "location_id",
            "location_name",
            "department_id",
            "department_name",
        ]

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return f"{obj.assigned_by.fname} {obj.assigned_by.lname}"
        return None
    
__all__ = [
    "UserWriteSerializer",
    "UserReadSerializerFull",
    "UserAreaSerializer",
    "UserPlacementWriteSerializer",
    'UserProfileSerializer',
    'UserTransferSerializer',
    'UserAccessoryAssignmentSerializer',
    'UserConsumableIssueSerializer'
]