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
    purchase_price = factory.Faker( "pydecimal", left_digits=5, right_digits=2, positive=True, )
    purchase_date = factory.Faker( "date_between", start_date="-5y", end_date="today", )
    room = factory.SubFactory(RoomFactory)


class ComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Component

    name = factory.Sequence(lambda n: f'Component {n}')
    brand = factory.Faker("company")
    model = factory.Faker("word")
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    quantity = factory.Faker("random_int", min=1, max=40)
    # unit_cost = factory.Faker( "pydecimal", left_digits=4, right_digits=2, positive=True, )
    equipment = factory.SubFactory(EquipmentFactory)


class AccessoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Accessory

    name = factory.Sequence(lambda n: f'Accessory {n}')
    serial_number = factory.Sequence(lambda n: f'SN{n}')
    quantity = factory.Faker("random_int", min=1, max=100)
    unit_cost = factory.Faker( "pydecimal", left_digits=4, right_digits=2, positive=True, )

    room = factory.SubFactory(RoomFactory)


class ConsumableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consumable

    name = factory.Sequence(lambda n: f'Consumable {n}')
    description = factory.Faker("text", max_nb_chars=50)
    quantity = factory.Faker("random_int", min=1, max=100)
    unit_cost = factory.Faker( "pydecimal", left_digits=4, right_digits=2, positive=True, )
    room = factory.SubFactory(RoomFactory)