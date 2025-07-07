import factory
from db_inventory.models import User, Department, Location, Equipment, Component, Accessory, UserDepartment, Consumable

from faker import Faker
fake = Faker()




class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker('email')
    fname = factory.Faker('first_name')
    lname = factory.Faker('last_name')
    job_title = factory.Faker('job')

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

class UserDepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserDepartment

    user = factory.SubFactory(UserFactory)
    department = factory.Iterator(Department.objects.all())
    date_joined = factory.LazyFunction(fake.date_time_this_decade)


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    address1 = factory.LazyFunction(fake.street_address)
    address2 = factory.LazyFunction(fake.secondary_address)
    city = factory.LazyFunction(fake.city)
    country = factory.LazyFunction(fake.country)


class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    name = factory.Sequence(lambda n: 'Equipment %d' % n)
    brand = fake.company()
    model = fake.word()
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    department = factory.Iterator(Department.objects.all())
    location = factory.Iterator(Location.objects.all())

class ComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Component

    name = factory.Sequence(lambda n: 'Component %d' % n)
    brand = fake.company()
    model = fake.word()
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    
    equipment = factory.Iterator(Equipment.objects.all())

class AccessoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Accessory

    name = factory.Sequence(lambda n: 'Accessory %d' % n)
    serial_number = factory.Sequence(lambda n: 'SN%d' % n)
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=100))
    
    department = factory.Iterator(Department.objects.all())


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: 'Consumable %d' % n)
    description = fake.text(max_nb_chars=50)
    quantity = fake.random_int(min=1, max=100)

    location = factory.Iterator(Location.objects.all())
    department = factory.Iterator(Department.objects.all())
