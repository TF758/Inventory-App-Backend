import factory
from sites.models.sites import Department, Location, Room
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
