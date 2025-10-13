from rest_framework import viewsets
from ..serializers.users import  UserReadSerializerFull, UserWriteSerializer, UserAreaSerializer, UserLocationWriteSerializer
from django.db.models import Case, When, Value, IntegerField
from ..models import User, UserLocation
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import UserFilter, UserLocationFilter
from ..mixins import ScopeFilterMixin
from ..pagination import FlexiblePagination
from ..permissions import UserPermission
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status

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
    

    def get_queryset(self):
        qs = super().get_queryset()
        search_term = self.request.query_params.get('search', None)

        if search_term:
            # Annotate results: 1 if starts with search_term, 2 otherwise
            qs = qs.annotate(
                starts_with_order=Case(
                    When(name__istartswith=search_term, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).order_by('starts_with_order', 'email')  # starts-with results first

        return qs
    
    def create(self, request, *args, **kwargs):
        """
        Custom create method that returns the new user's public_id
        and summary info after creation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # return newly created user
        read_data = UserReadSerializerFull(user, context={'request': request}).data
        headers = self.get_success_headers(serializer.data)
        return Response(read_data, status=status.HTTP_201_CREATED, headers=headers)



class UserLocationViewSet(viewsets.ModelViewSet):
    """
    Manage UserLocation records — assigning users to rooms, and viewing their
    associated location/department hierarchy.
    """

    queryset = UserLocation.objects.select_related(
        "user", "room", "room__location", "room__location__department"
    ).all()
    serializer_class = UserAreaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = UserLocationFilter
  

    def get_serializer_class(self):
        if self.action in ["update", "partial_update", "create"]:
            return UserLocationWriteSerializer
        return UserAreaSerializer

    def get_queryset(self):
        """
        Optionally filter by user, room, location, or department via query params.
        Example: /api/user-locations/?department_id=DPT123ABC
        """
        queryset = self.queryset
        user_id = self.request.query_params.get("user_id")
        room_id = self.request.query_params.get("room_id")
        location_id = self.request.query_params.get("location_id")
        department_id = self.request.query_params.get("department_id")

        if user_id:
            queryset = queryset.filter(user__public_id=user_id)
        if room_id:
            queryset = queryset.filter(room__public_id=room_id)
        if location_id:
            queryset = queryset.filter(room__location__public_id=location_id)
        if department_id:
            queryset = queryset.filter(room__location__department__public_id=department_id)

        return queryset

    def perform_create(self, serializer):
        """
        Create a UserLocation — validation handled by serializer.
        """
        serializer.save()

