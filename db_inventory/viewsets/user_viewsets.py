from rest_framework import viewsets
from ..serializers.users import UserPrivateSerializer, UserReadSerializerFull, UserWriteSerializer
from django.db.models import Case, When, Value, IntegerField
from ..models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import UserFilter
from ..mixins import ScopeFilterMixin
from ..pagination import FlexiblePagination


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


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
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
