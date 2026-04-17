from db_inventory.models import User
import factory
from faker import Faker
import random
from django.utils import timezone


from db_inventory.models.roles import RoleAssignment
from sites.factories.site_factories import DepartmentFactory, LocationFactory, RoomFactory
from sites.models.sites import UserPlacement

fake = Faker()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall("set_password", "password")
    job_title = factory.LazyFunction(lambda: fake.job()[:50])
    force_password_change = False
    is_active = factory.LazyFunction(
        lambda: random.choices([True, False], weights=[0.85, 0.15])[0]
    )
    public_id = factory.Sequence(lambda n: f"UID{n:08d}")
    is_staff = False
    is_superuser = False


class AdminUserFactory(UserFactory):
    email = factory.Sequence(lambda n: f"admin{n}@gmail.com")
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    is_staff = True
    is_superuser = True


class UserPlacementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserPlacement

    user = factory.SubFactory(UserFactory)
    room = None
    is_current = True
    date_joined = factory.LazyFunction(timezone.now)




class RoleAssignmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = RoleAssignment

    user = factory.SubFactory(UserFactory)

    role = "SITE_ADMIN"

    department = None
    location = None
    room = None

    assigned_by = factory.SubFactory(UserFactory)

    class Params:

        site_admin = factory.Trait(
            role="SITE_ADMIN",
            department=None,
            location=None,
            room=None,
        )

        department_role = factory.Trait(
            role="DEPARTMENT_ADMIN",
            department=factory.SubFactory(DepartmentFactory),
            location=None,
            room=None,
        )

        location_role = factory.Trait(
            role="LOCATION_ADMIN",
            department=None,
            location=factory.SubFactory(LocationFactory),
            room=None,
        )

        room_role = factory.Trait(
            role="ROOM_ADMIN",
            department=None,
            location=None,
            room=factory.SubFactory(RoomFactory),
        )