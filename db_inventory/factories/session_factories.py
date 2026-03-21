from db_inventory.models.security import UserSession
import factory
from django.utils import timezone
from datetime import timedelta
import secrets

from .user_factories import UserFactory

class UserSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    status = UserSession.Status.ACTIVE
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))