from core.models.sessions import UserSession
import factory
from django.utils import timezone
from datetime import timedelta
import uuid
from users.factories.user_factories import UserFactory



class UserSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    status = UserSession.Status.ACTIVE
    expires_at = factory.LazyFunction( lambda: timezone.now() + timedelta(days=7) )
    absolute_expires_at = factory.LazyFunction( lambda: timezone.now() + timedelta(days=30) )
    last_used_at = factory.LazyFunction(timezone.now)
    refresh_token_hash = factory.LazyFunction( lambda: uuid.uuid4().hex )