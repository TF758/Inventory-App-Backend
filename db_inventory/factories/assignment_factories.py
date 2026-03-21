import factory
from django.utils import timezone
from db_inventory.models.asset_assignment import ( EquipmentAssignment, AccessoryAssignment, ConsumableIssue, )
from .user_factories import UserFactory
from .asset_factories import EquipmentFactory, AccessoryFactory, ConsumableFactory


class EquipmentAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EquipmentAssignment

    equipment = factory.SubFactory(EquipmentFactory)
    user = factory.SubFactory(UserFactory)
    assigned_by = factory.SelfAttribute("user")

    assigned_at = factory.LazyFunction(timezone.now)
    returned_at = None
    notes = factory.Faker("sentence")


class AccessoryAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccessoryAssignment

    accessory = factory.SubFactory(AccessoryFactory)
    user = factory.SubFactory(UserFactory)

    quantity = factory.Faker("random_int", min=1, max=10)
    assigned_by = factory.SelfAttribute("user")

    assigned_at = factory.LazyFunction(timezone.now)
    returned_at = None


class ConsumableIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConsumableIssue

    consumable = factory.SubFactory(ConsumableFactory)
    user = factory.SubFactory(UserFactory)

    issued_quantity = factory.Faker("random_int", min=5, max=20)
    quantity = factory.LazyAttribute(lambda o: o.issued_quantity)

    assigned_by = factory.SelfAttribute("user")

    assigned_at = factory.LazyFunction(timezone.now)
    returned_at = None
    purpose = factory.Faker("sentence")