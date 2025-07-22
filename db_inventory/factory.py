import factory
from db_inventory.models import User, Department, Location, Equipment, Component, Accessory, Consumable, UserLocation

from faker import Faker
fake = Faker()




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

class UserLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserLocation

    user = factory.SubFactory(UserFactory)
    location = factory.Iterator(Location.objects.all())
    date_joined = factory.LazyFunction(fake.date_time_this_decade)


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    name = factory.LazyFunction(fake.company)
    room  = f"{fake.color_name()} {fake.word().capitalize()} Room"
    area = f"{fake.color_name()} {fake.word().capitalize()} Area"
    section =  f"{fake.color_name()} {fake.word().capitalize()} Section"
    department = factory.Iterator (Department.objects.all())


class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    name = factory.Sequence(lambda n: 'Equipment %d' % n)
    brand = fake.company()
    model = fake.word()
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    location = factory.Iterator(Location.objects.all())

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
    location = factory.Iterator(Location.objects.all())


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: 'Consumable %d' % n)
    description = fake.text(max_nb_chars=50)
    quantity = fake.random_int(min=1, max=100)
    location = factory.Iterator(Location.objects.all())
 
