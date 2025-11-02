from rest_framework import viewsets
from ..serializers.users import  UserReadSerializerFull, UserWriteSerializer, UserAreaSerializer, UserLocationWriteSerializer
from django.db.models import Case, When, Value, IntegerField
from ..models import User, UserLocation, RoleAssignment, Department
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import UserFilter, UserLocationFilter
from ..mixins import ScopeFilterMixin
from ..pagination import FlexiblePagination
from db_inventory.permissions import UserPermission, UserLocationPermission, is_in_scope, filter_queryset_by_scope
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

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

    def get_queryset(self):
        user = self.request.user
        return filter_queryset_by_scope(user, super().get_queryset(), UserLocation)

    def perform_create(self, serializer):
        user = serializer.validated_data.get("user")
        room = serializer.validated_data.get("room")
        is_current = serializer.validated_data.get("is_current", False)

        # Object-level permission check
        if not self.request.user.has_perm("add_userlocation") and not is_in_scope(self.request.user.active_role, room=room):
            raise PermissionDenied("Cannot assign user to a room outside your scope.")

        if is_current:
            UserLocation.objects.filter(user=user, is_current=True).update(is_current=False)

        serializer.save()

    def perform_update(self, serializer):
        user_location = serializer.instance
        room = serializer.validated_data.get("room", user_location.room)
        is_current = serializer.validated_data.get("is_current", user_location.is_current)

        if not self.request.user.has_perm("change_userlocation") and not is_in_scope(self.request.user.active_role, room=room):
            raise PermissionDenied("Cannot assign user to a room outside your scope.")

        if is_current:
            UserLocation.objects.filter(user=user_location.user, is_current=True).exclude(pk=user_location.pk).update(is_current=False)

        serializer.save()


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