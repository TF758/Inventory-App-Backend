import factory
from django.utils import timezone
from datetime import timedelta

from db_inventory.factories.user_factories import UserFactory
from db_inventory.models.users import PasswordResetEvent


class PasswordResetEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PasswordResetEvent

    user = factory.SubFactory(UserFactory)

    admin = None

    token = factory.Faker("uuid4")

    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=1)
    )

    used_at = None

    is_active = True