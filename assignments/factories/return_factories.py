import factory
from django.utils import timezone

from assignments.models.asset_assignment import (
    ReturnRequest,
    ReturnRequestItem,
)
from assignments.factories.assignment_factories import AccessoryAssignmentFactory, ConsumableIssueFactory, EquipmentAssignmentFactory
from users.factories.user_factories import UserFactory



class ReturnRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReturnRequest

    requester = factory.SubFactory(UserFactory)
    status = ReturnRequest.Status.PENDING
    notes = factory.Faker("sentence")

    processed_by = None
    processed_at = None

    @factory.post_generation
    def set_processed(obj, create, extracted, **kwargs):
        if not create:
            return

        if obj.status != ReturnRequest.Status.PENDING:
            obj.processed_by = obj.requester
            obj.processed_at = timezone.now()
            obj.save()

class ReturnRequestItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReturnRequestItem

    return_request = factory.SubFactory(ReturnRequestFactory)
    status = ReturnRequestItem.Status.PENDING
    notes = factory.Faker("sentence")

    verified_by = None
    verified_at = None


class EquipmentReturnItemFactory(ReturnRequestItemFactory):
    item_type = ReturnRequestItem.ItemType.EQUIPMENT

    equipment_assignment = factory.SubFactory(EquipmentAssignmentFactory)

    accessory_assignment = None
    consumable_issue = None

    quantity = None

    room = factory.LazyAttribute(
        lambda obj: obj.equipment_assignment.equipment.room
    )

class AccessoryReturnItemFactory(ReturnRequestItemFactory):
    item_type = ReturnRequestItem.ItemType.ACCESSORY

    accessory_assignment = factory.SubFactory(AccessoryAssignmentFactory)

    equipment_assignment = None
    consumable_issue = None

    quantity = factory.Faker("random_int", min=1, max=5)

    room = factory.LazyAttribute(
        lambda obj: obj.accessory_assignment.accessory.room
    )

class ConsumableReturnItemFactory(ReturnRequestItemFactory):
    item_type = ReturnRequestItem.ItemType.CONSUMABLE

    consumable_issue = factory.SubFactory(ConsumableIssueFactory)

    equipment_assignment = None
    accessory_assignment = None

    quantity = factory.Faker("random_int", min=1, max=5)

    room = factory.LazyAttribute(
        lambda obj: obj.consumable_issue.consumable.room
    )