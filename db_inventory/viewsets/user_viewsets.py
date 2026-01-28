from rest_framework import viewsets
from db_inventory.serializers.users import  UserProfileSerializer, UserReadSerializerFull, UserWriteSerializer, UserAreaSerializer, UserLocationWriteSerializer
from db_inventory.serializers.roles import RoleWriteSerializer
from rest_framework import status, views
from django.db import transaction
from db_inventory.models import User, UserLocation, RoleAssignment, Room, Department, Location
from db_inventory.models.roles import RoleAssignment
from db_inventory.models.site import UserLocation, Room, Department, Location
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import  UserFilter, UserLocationFilter
from db_inventory.mixins import ScopeFilterMixin
from db_inventory.pagination import FlexiblePagination
from db_inventory.permissions import UserPermission, RolePermission, UserLocationPermission, is_in_scope, filter_queryset_by_scope, FullUserCreatePermission
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from db_inventory.mixins import AuditMixin
from db_inventory.permissions.helpers import ensure_permission
from django.db.models import Count, Q
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin


from db_inventory.permissions.users import CanViewUserProfile
from db_inventory.models.asset_assignment import EquipmentAssignment
from db_inventory.serializers.self import SelfAssignedEquipmentSerializer

class UserModelViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet):
    """
    User directory + self-service profile updates.

    - Read users
    - Users may update themselves
    - No user creation
    - No admin actions
    """

    queryset = User.objects.all().order_by("-id")
    serializer_class = UserReadSerializerFull
    lookup_field = "public_id"

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["^email", "email"]
    filterset_class = UserFilter
    pagination_class = FlexiblePagination

    permission_classes = [UserPermission]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UserWriteSerializer
        return UserReadSerializerFull

    def get_queryset(self):
        user = self.request.user
        active_role = getattr(user, "active_role", None)

        qs = User.objects.all().order_by("-id")

        if self.action == "list" and active_role:
            qs = filter_queryset_by_scope(user, qs, User)

        return qs



class UserLocationViewSet(viewsets.ModelViewSet):
    queryset = UserLocation.objects.select_related(
        "user", "room", "room__location", "room__location__department"
    ).order_by("-date_joined", "-id")

    serializer_class = UserAreaSerializer
    lookup_field = "public_id"
    permission_classes = [UserLocationPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserLocationFilter

    def get_object(self):
        obj = super().get_object()  # fetch object ignoring scope
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        if self.action == "list":
            # Only list objects within scope
            return filter_queryset_by_scope(self.request.user, super().get_queryset(), UserLocation)
        # For detail actions, return all objects (permission check will handle scope)
        return super().get_queryset()
    
    def get_serializer_class(self):
        if self.action in ["update", "partial_update", "create"]:
            return UserLocationWriteSerializer
        return UserAreaSerializer


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = UserAreaSerializer(serializer.instance, context=self.get_serializer_context())
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
    
    def perform_create(self, serializer):
        room = serializer.validated_data.get("room")
        if not self.request.user.has_perm("add_userlocation") and \
        not is_in_scope(self.request.user.active_role, room=room):
            raise PermissionDenied("Cannot assign user to a room outside your scope.")

        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read_serializer = UserAreaSerializer(instance, context=self.get_serializer_context())
        return Response(read_serializer.data)


class UserLocationByUserView(APIView):
    """
    Retrieves a user's location by using the user's public_id
    """

    def get(self, request, user_id: str):
        try:
            assignment = UserLocation.objects.select_related(
                "user", "room", "room__location", "room__location__department"
            ).get(user__public_id=user_id)
            serializer = UserAreaSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserLocation.DoesNotExist:
            return Response({"detail": "User has no location assignment"}, status=status.HTTP_404_NOT_FOUND)
        


class UnallocatedUserViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    Retrieve users not assigned to any room.
    """

    queryset = User.objects.filter(user_locations__isnull=True) 
    serializer_class = UserReadSerializerFull
    model_class = User

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^email', 'email']
    filterset_class = UserFilter
    pagination_class = FlexiblePagination
    permission_classes = [UserPermission]



class FullUserCreateView(AuditMixin,views.APIView):
    """
    Create a User, assign a UserLocation, and assign a Role atomically.
    This endpoint enforces:
      - SITE_ADMIN: can create users anywhere
      - DEPARTMENT_ADMIN: can create users only inside their department
      - LOCATION_ADMIN: cannot use this endpoint
      - ROOM_ADMIN: cannot use this endpoint
    """

    permission_classes = [FullUserCreatePermission]

    def post(self, request, *args, **kwargs):
        payload = request.data
        user_data = payload.get("user", {})
        user_location_public_id = payload.get("user_location")
        role_data = payload.get("role", {})

        user_location_instance = None

        with transaction.atomic():

            # 1️⃣ Create User
            user_serializer = UserWriteSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()

            # 2️⃣ Assign UserLocation (permission enforced here)
            if user_location_public_id:
                ul_serializer = UserLocationWriteSerializer(
                    data={
                        "user_id": user.public_id,
                        "room_id": user_location_public_id,
                    },
                    context={"request": request},
                )
                ul_serializer.is_valid(raise_exception=True)

                temp_ul = UserLocation(
                    user=user,
                    room=ul_serializer.validated_data["room"]
                )

                if not UserLocationPermission().has_object_permission(
                    request, self, temp_ul
                ):
                    raise PermissionDenied(
                        "You do not have permission to assign this location."
                    )

                user_location_instance = ul_serializer.save()

            # 3️⃣ Assign Role (permission enforced here)
            role_name = role_data.get("role")

            def resolve(model, public_id):
                if not public_id:
                    return None
                return model.objects.get(public_id=public_id)

            department = resolve(Department, role_data.get("department"))
            location = resolve(Location, role_data.get("location"))
            room = resolve(Room, role_data.get("room"))

            # Normalize scope based on role level
            if role_name.startswith("ROOM_"):
                department = None
                location = None
            elif role_name.startswith("LOCATION_"):
                department = None
                room = None
            elif role_name.startswith("DEPARTMENT_"):
                location = None
                room = None

            temp_role = RoleAssignment(
                user=user,
                role=role_name,
                department=department,
                location=location,
                room=room,
            )

            
            try:
                ensure_permission(
                    request.user,
                    role_name,
                    room=room,
                    location=location,
                    department=department,
                )
            except PermissionDenied:
                raise PermissionDenied("You do not have permission to assign this role.")

            role_serializer = RoleWriteSerializer(
                data={
                    "user": user.public_id,
                    "role": role_name,
                    "department": department.public_id if department else None,
                    "location": location.public_id if location else None,
                    "room": room.public_id if room else None,
                },
                context={"request": request},
            )
            role_serializer.is_valid(raise_exception=True)
            role_assignment = role_serializer.save()

        return Response(
            {
                "user": UserWriteSerializer(user).data,
                "user_location": (
                    UserLocationWriteSerializer(user_location_instance).data
                    if user_location_instance else None
                ),
                "role_assignment": RoleWriteSerializer(role_assignment).data,
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileViewSet(RetrieveModelMixin, GenericViewSet):
    """
    Retrieve a single user profile by public_id.
    """

    permission_classes = [CanViewUserProfile]
    serializer_class = UserProfileSerializer
    lookup_field = "public_id"

    queryset = (
        User.objects
        .filter(is_active=True)
        .annotate(
            equipment_count=Count(
                "equipment_assignments",
                filter=Q(
                    equipment_assignments__returned_at__isnull=True
                ),
                distinct=True,
            ),
            accessory_count=Count(
                "accessory_assignments__accessory",
                filter=Q(
                    accessory_assignments__returned_at__isnull=True,
                    accessory_assignments__quantity__gt=0,
                ),
                distinct=True,
            ),
            consumable_count=Count(
                "consumable_assignments__consumable",
                filter=Q(
                    consumable_assignments__returned_at__isnull=True,
                    consumable_assignments__quantity__gt=0,
                ),
                distinct=True,
            ),
        )
    )