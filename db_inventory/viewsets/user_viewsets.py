from rest_framework import viewsets
from ..serializers.users import UserPrivateSerializer

from ..models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import UserFilter
from ..mixins import ScopeFilterMixin


class UserModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing User objects.
This viewset provides `list`, `create`, actions for User objects."""

    queryset = User.objects.all().order_by('-id')
    serializer_class = UserPrivateSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['email']

    filterset_class = UserFilter
