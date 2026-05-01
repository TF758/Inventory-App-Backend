import factory
from faker import Faker
from assets.models.assets import Accessory, Component, Consumable, Equipment
from sites.factories.site_factories import RoomFactory

fake = Faker()

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
    quantity = factory.Faker("random_int", min=1, max=100)
    room = factory.SubFactory(RoomFactory)


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: f'Consumable {n}')
    description = factory.Faker("text", max_nb_chars=50)
    quantity = factory.Faker("random_int", min=1, max=100)
    room = factory.SubFactory(RoomFactory)