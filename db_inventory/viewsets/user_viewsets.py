from rest_framework import viewsets
from ..serializers.users import  UserReadSerializerFull, UserWriteSerializer
from django.db.models import Case, When, Value, IntegerField
from ..models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import UserFilter
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

