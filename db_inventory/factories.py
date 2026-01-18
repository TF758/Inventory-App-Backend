import factory
from db_inventory.models import User, Department, Location, Equipment, Component, Accessory, Consumable, UserLocation, Room
from faker import Faker
import random
from django.utils import timezone
from datetime import timedelta
from db_inventory.models.security import UserSession
import secrets

fake = Faker()

DEPARTMENT_IMAGE_URLS = [
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQeNHmcybimV62sCsu5LH5zWYkq6TUti8srg&s",
    "https://publicservice.govt.lc/images/528px-Coat_of_Arms_of_Saint_Lucia.svg.png",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRj6PTPMvpZw-9CRvnUcvrO-1mEDuBLtEyybQ&s",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQV8tXEYcWeRO2y4R6lUie3TKQ0QqgJXDt2Fw&s",
    "https://scontent-mia3-2.xx.fbcdn.net/v/t39.30808-6/251905257_283920967072718_3803379083888235439_n.jpg"
]


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    job_title = factory.LazyFunction(lambda: fake.job()[:50])
    is_active = factory.LazyFunction(lambda: random.choices([True, False], weights=[0.85, 0.15])[0])  # 85% active, 15% inactive
    public_id = factory.Sequence(lambda n: f"UID{n:08d}")
    is_staff = False
    is_superuser = False


class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = "admin@gmail.com"
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    job_title = factory.LazyFunction(lambda: fake.job()[:50])
    is_staff = True
    is_superuser = True


class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department

    name = factory.Sequence(lambda n: f'Department {n}')
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=20))
    img_link = factory.LazyFunction(lambda: random.choice(DEPARTMENT_IMAGE_URLS))


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    name = factory.Sequence(lambda n: f"Location {n}")
    department = factory.SubFactory(DepartmentFactory)


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    name = factory.Sequence(lambda n: f"Room {n}")
    location = factory.SubFactory(LocationFactory)

class UserLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserLocation

    user = None  # Must be provided when creating
    room = None  # Optional; if None, user has no location
    is_current = True
    date_joined = factory.LazyFunction(lambda: timezone.make_aware(fake.date_time_this_decade()))

    @factory.post_generation
    def assign_room(obj, create, extracted, **kwargs):
        """
        Ensure room assignment is only set if provided.
        Allows skipping location for some users.
        """
        if not create:
            return
        if extracted:  # If a room is passed in
            obj.room = extracted
            obj.save()


class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    name = factory.Sequence(lambda n: f'Equipment {n}')
    brand = factory.LazyFunction(fake.company)
    model = factory.LazyFunction(fake.word)
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    room = factory.SubFactory(RoomFactory)


class ComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Component

    name = factory.Sequence(lambda n: f'Component {n}')
    brand = factory.Faker("company")
    model = factory.Faker("word")
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    quantity = factory.Faker("random_int", min=1, max=40)
    equipment = factory.SubFactory(EquipmentFactory)


class AccessoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Accessory

    name = factory.Sequence(lambda n: f'Accessory {n}')
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=100))
    room = factory.SubFactory(RoomFactory)


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: f'Consumable {n}')
    description = factory.Faker("text", max_nb_chars=50)
    quantity = factory.Faker("random_int", min=1, max=100)
    room = factory.SubFactory(RoomFactory)

class UserSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    status = UserSession.Status.ACTIVE

    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=7)
    )

    absolute_expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=30)
    )

    ip_address = factory.Faker("ipv4")
    user_agent = factory.Faker("user_agent")

    user_agent_hash = factory.LazyAttribute(
        lambda o: UserSession.hash_user_agent(o.user_agent)
    )
    refresh_token_hash = factory.LazyFunction(
        lambda: UserSession.hash_token(secrets.token_urlsafe(64))
    )
    previous_refresh_token_hash = None

    @factory.post_generation
    def attach_raw_refresh(obj, create, extracted, **kwargs):
        if not create:
            return
        obj.raw_refresh = extracted or secrets.token_urlsafe(64)
