from rest_framework import viewsets
from ..serializers.users import  UserReadSerializerFull, UserWriteSerializer, UserAreaSerializer, UserLocationWriteSerializer
from db_inventory.serializers.roles import RoleWriteSerializer
from rest_framework import status, views
from django.db import transaction
from db_inventory.models import User, UserLocation, RoleAssignment, Room, Department, Location
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import UserFilter, UserLocationFilter
from ..mixins import ScopeFilterMixin
from ..pagination import FlexiblePagination
from db_inventory.permissions import UserPermission, RolePermission, UserLocationPermission, is_in_scope, filter_queryset_by_scope
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

class UserModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing User objects.
This viewset provides `list`, `create`, actions for User objects."""

    queryset = User.objects.all().order_by('-id')
    serializer_class = UserReadSerializerFull
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^email', 'email']

    filterset_class = UserFilter

    pagination_class = FlexiblePagination

    permission_classes = [UserPermission]


    def get_serializer_class(self):
        if self.action in ["update", "partial_update", "create"]:
            return UserWriteSerializer
        return UserReadSerializerFull
    

    # def get_queryset(self):
    #     qs = super().get_queryset()
    #     user = self.request.user
    #     active_role = getattr(user, "active_role", None)

    #     # Always include self
    #     qs = qs.filter(Q(id=user.id) | Q(active_role__isnull=False))

    #     if active_role:
    #         # Only filter users within scope for non-self
    #         scoped_qs = filter_queryset_by_scope(user, qs, User)
    #         qs = qs.filter(Q(id__in=scoped_qs.values("id")) | Q(id=user.id))
    #     else:
    #         # Only self if no role
    #         qs = qs.filter(id=user.id)

    #     # Search
    #     search_term = self.request.query_params.get('search', None)
    #     if search_term:
    #         qs = qs.annotate(
    #             starts_with_order=Case(
    #                 When(fname__istartswith=search_term, then=Value(1)),
    #                 default=Value(2),
    #                 output_field=IntegerField()
    #             )
    #         ).order_by('starts_with_order', 'email')

    #     return qs.distinct()


    def get_queryset(self):
        user = self.request.user
        active_role = getattr(user, "active_role", None)

        # Start with all users (like the "bare minimum" that worked)
        qs = User.objects.all().order_by("-id")

        # Only apply scoping for list requests
        if self.action == "list" and active_role:
            qs = filter_queryset_by_scope(user, qs, User)

        return qs


    # def get_queryset(self):
    #         qs = super().get_queryset()
    #         user = self.request.user
    #         active_role = getattr(user, "active_role", None)

    #         if active_role:
    #             # Users in scope
    #             scoped_qs_ids = filter_queryset_by_scope(user, qs, User).values_list("id", flat=True)
    #             # Include self + scoped users
    #             qs = qs.filter(Q(id__in=scoped_qs_ids) | Q(id=user.id))
    #         else:
    #             # Only self if no role
    #             qs = qs.filter(id=user.id)

    #         # Optional: search
    #         search_term = self.request.query_params.get("search", None)
    #         if search_term:
    #             qs = qs.annotate(
    #                 starts_with_order=Case(
    #                     When(fname__istartswith=search_term, then=Value(1)),
    #                     default=Value(2),
    #                     output_field=IntegerField(),
    #                 )
    #             ).order_by("starts_with_order", "email")

    #         return qs.distinct()
            

    def create(self, request, *args, **kwargs):
        """
        Custom create method that automatically sets `created_by` to the current user
        and returns the new user's public_id and summary info after creation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Pass created_by automatically
        user = serializer.save(created_by=request.user)

        # Assign a default role if creator has an active_role
        # get a department
        # assigning a default department for testing
        # default_department = Department.objects.first()

        # if not user.active_role and request.user.active_role:
        #     default_role = RoleAssignment.objects.create(
        #         user=user,
        #         role="DEPARTMENT_VIEWER",
        #         department=default_department,
        #         assigned_by=request.user,
        #     )
        #     user.active_role = default_role
        user.is_active = True
        user.save()

        # Return the newly created user (using the read serializer)
        read_data = UserReadSerializerFull(user, context={'request': request}).data
        headers = self.get_success_headers(serializer.data)
        return Response(read_data, status=status.HTTP_201_CREATED, headers=headers)



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

    queryset = User.objects.filter(user_locations__isnull=True)  # ✅ fixed reverse name
    serializer_class = UserReadSerializerFull
    model_class = User

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^email', 'email']
    filterset_class = UserFilter
    pagination_class = FlexiblePagination
    permission_classes = [UserPermission]



class FullUserCreateView(views.APIView):
    """
    Create a User, assign a UserLocation, and assign a Role atomically.
    Payload format:
    {
        "user": { ...user fields... },
        "user_location": "room_public_id",        # optional
        "role": { ...role fields (excluding 'user') }
    }
    """

    def post(self, request, *args, **kwargs):
        payload = request.data
        user_data = payload.get("user", {})
        user_location_public_id = payload.get("user_location")
        role_data = payload.get("role", {})

        # --- Permission checks for authenticated user ---
        user_perm = UserPermission()
        location_perm = UserLocationPermission()
        role_perm = RolePermission()

        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        with transaction.atomic():
            # --- 1️⃣ Create User ---
            user_serializer = UserWriteSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()

            # --- 2️⃣ Assign UserLocation if provided ---
            user_location_instance = None
            if user_location_public_id:
                location_data = {
                    "user_id": user.public_id,
                    "room_id": user_location_public_id
                }
                ul_serializer = UserLocationWriteSerializer(data=location_data)
                ul_serializer.is_valid(raise_exception=True)

                # Check object-level permission
                temp_ul = UserLocation(user=user, room=ul_serializer.validated_data["room"])
                if not location_perm.has_object_permission(request, self, temp_ul):
                    raise PermissionDenied("You do not have permission to assign this location.")

                user_location_instance = ul_serializer.save()

            # --- 3️⃣ Assign Role ---
            role_data_for_check = role_data.copy()

            # Resolve foreign keys to actual model instances
            department_id = role_data_for_check.pop("department", None)
            location_id = role_data_for_check.pop("location", None)
            room_id = role_data_for_check.pop("room", None)

            department = None
            location = None
            room = None

            if department_id:
                try:
                    department = Department.objects.get(public_id=department_id)
                except Department.DoesNotExist:
                    raise ValidationError({"department": "Invalid department public_id."})

            if location_id:
                try:
                    location = Location.objects.get(public_id=location_id)
                except Location.DoesNotExist:
                    raise ValidationError({"location": "Invalid location public_id."})

            if room_id:
                try:
                    room = Room.objects.get(public_id=room_id)
                except Room.DoesNotExist:
                    raise ValidationError({"room": "Invalid room public_id."})

            # Build temporary role instance for permission check
            temp_role = RoleAssignment(
                user=user,
                role=role_data_for_check.get("role"),
                department=department,
                location=location,
                room=room
            )

            # Check object-level permission
            if not role_perm.has_object_permission(request, self, temp_role):
                raise PermissionDenied("You do not have permission to assign this role.")

            # Use serializer to save (assign user automatically)
            role_data_for_save = role_data.copy()
            role_data_for_save["user"] = user.public_id
            role_serializer = RoleWriteSerializer(data=role_data_for_save, context={"request": request})
            role_serializer.is_valid(raise_exception=True)
            role_assignment = role_serializer.save()

        # --- Build response ---
        response_data = {
            "user": UserWriteSerializer(user).data,
            "user_location": UserLocationWriteSerializer(user_location_instance).data if user_location_instance else None,
            "role_assignment": RoleWriteSerializer(role_assignment).data
        }

        return Response(response_data, status=status.HTTP_201_CREATED)