import factory
from db_inventory.models import User, Department, Location, Equipment, Component, Accessory, Consumable, UserLocation, Room

from faker import Faker
fake = Faker()

DEPARTMENT_IMAGE_URLS = [
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQeNHmcybimV62sCsu5LH5zWYkq6TUti8srg&s",
     "https://publicservice.govt.lc/images/528px-Coat_of_Arms_of_Saint_Lucia.svg.png",
     "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRj6PTPMvpZw-9CRvnUcvrO-1mEDuBLtEyybQ&s",
     "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQV8tXEYcWeRO2y4R6lUie3TKQ0QqgJXDt2Fw&s",
     "https://scontent-mia3-2.xx.fbcdn.net/v/t39.30808-6/251905257_283920967072718_3803379083888235439_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=6ee11a&_nc_ohc=zh56Ocy31UwQ7kNvwH0kgi1&_nc_oc=Adl5QhBteM4aCNrffbanHJMczjztnBo4JGfxE0C7bT3B_sHA9_LgMXcmme4S3UtDtLw&_nc_zt=23&_nc_ht=scontent-mia3-2.xx&_nc_gid=H0hszqkNv_moEWvHANAxDg&oh=00_AfUbfh4jHzHm8-ZW6bTb6gg_igSOZ5hugBDQtpc9itqPLw&oe=68A1B10E"

]



class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker('email')
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    job_title = factory.Faker('job')
    is_active = factory.Faker("boolean")

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

    name = factory.Sequence(lambda n: 'Department %d' % n)
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=20))
    img_link = factory.LazyFunction(lambda: fake.random_element(elements=DEPARTMENT_IMAGE_URLS))


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    name = factory.LazyFunction(fake.company)
    department = factory.Iterator (Department.objects.all())


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    location = factory.Iterator (Location.objects.all())
    name = factory.LazyFunction(fake.color_name)
    area = factory.LazyFunction(fake.company)
    section =  f"{fake.color_name()} Section"

class UserLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserLocation

    user =  factory.Iterator(User.objects.all())
    room = factory.Iterator(Room.objects.all())
    date_joined = factory.LazyFunction(fake.date_time_this_decade)

class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    name = factory.Sequence(lambda n: 'Equipment %d' % n)
    brand = fake.company()
    model = fake.word()
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    room = factory.Iterator(Room.objects.all())

class ComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Component

    name = factory.Sequence(lambda n: 'Component %d' % n)
    brand = fake.company()
    model = fake.word()
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=40))
    equipment = factory.Iterator(Equipment.objects.all())

class AccessoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Accessory

    name = factory.Sequence(lambda n: 'Accessory %d' % n)
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=100))
    room = factory.Iterator(Room.objects.all())


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: 'Consumable %d' % n)
    description = fake.text(max_nb_chars=50)
    quantity = fake.random_int(min=1, max=100)
    room = factory.Iterator(Room.objects.all())
 
