import factory
from db_inventory.models import User, Department, Location, Equipment, Component, Accessory, Consumable, UserLocation, Room
from faker import Faker
import random

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

    email = factory.Sequence(lambda n: f"{fake.first_name().lower()}.{fake.last_name().lower()}.{n}@example.com")
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    job_title = factory.Faker('job')
    is_active = True


class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = "admin@gmail.com"
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    job_title = factory.Faker('job')
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

    name = factory.LazyFunction(fake.company)
    department = factory.LazyFunction(lambda: random.choice(Department.objects.all()))


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    name = factory.LazyFunction(fake.color_name)
    location = factory.LazyFunction(lambda: random.choice(Location.objects.all()))
    area = factory.LazyFunction(fake.company)
    section = factory.LazyFunction(lambda: f"{fake.color_name()} Section")


class UserLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserLocation

    user = factory.SubFactory(UserFactory)
    room = factory.LazyFunction(lambda: random.choice(Room.objects.all()))
    date_joined = factory.LazyFunction(fake.date_time_this_decade)


class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    name = factory.Sequence(lambda n: f'Equipment {n}')
    brand = factory.LazyFunction(fake.company)
    model = factory.LazyFunction(fake.word)
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    room = factory.LazyFunction(lambda: random.choice(Room.objects.all()))


class ComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Component

    name = factory.Sequence(lambda n: f'Component {n}')
    brand = factory.LazyFunction(fake.company)
    model = factory.LazyFunction(fake.word)
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=40))
    equipment = factory.LazyFunction(lambda: random.choice(Equipment.objects.all()))


class AccessoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Accessory

    name = factory.Sequence(lambda n: f'Accessory {n}')
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=100))
    room = factory.LazyFunction(lambda: random.choice(Room.objects.all()))


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: f'Consumable {n}')
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=50))
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=100))
    room = factory.LazyFunction(lambda: random.choice(Room.objects.all()))
