from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef,  Subquery, Sum,  F, IntegerField, Value
from django.db.models.functions import Coalesce, Greatest
from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment, ReturnRequest, ReturnRequestItem
from db_inventory.models.assets import Equipment
from users.models.users import User
from django.db.models import Q

def get_user(public_id):
    return get_object_or_404(User, public_id=public_id, is_active=True)


def get_user_equipment(user):
    return Equipment.objects.filter(
        active_assignment__user=user,
        active_assignment__returned_at__isnull=True,
        is_deleted=False,
    )

def get_user_equipment_assignments(user):
    return EquipmentAssignment.objects.filter(
        user=user,
        returned_at__isnull=True,
        equipment__is_deleted=False,
    )

def get_user_equipment_with_meta(user):
    pending_return_requests = ReturnRequestItem.objects.filter(
        equipment_assignment=OuterRef("pk"),
        return_request__status=ReturnRequest.Status.PENDING
    )

    return (
        get_user_equipment_assignments(user)
        .select_related(
            "equipment",
            "equipment__room",
            "equipment__room__location",
            "equipment__room__location__department",
        )
        .annotate(
            has_pending_return_request=Exists(pending_return_requests)
        )
    )

def get_user_accessories_with_meta(user):
    pending_items = ReturnRequestItem.objects.filter(
        accessory_assignment=OuterRef("pk"),
        return_request__status=ReturnRequest.Status.PENDING,
    )

    pending_qty_subquery = (
        pending_items
        .values("accessory_assignment")
        .annotate(total=Sum("quantity"))
        .values("total")
    )

    return (
        get_user_accessories(user)
        .select_related(
            "accessory",
            "accessory__room",
            "accessory__room__location",
        )
        .annotate(
            pending_return_quantity=Coalesce(
                Subquery(pending_qty_subquery[:1], output_field=IntegerField()),
                Value(0),
            ),
            has_pending_return_request=Exists(pending_items),
            available_return_quantity=Greatest(
                F("quantity") - F("pending_return_quantity"),
                Value(0),
            ),
        )
    )

def get_user_consumables_with_meta(user):
    pending_items = ReturnRequestItem.objects.filter(
        consumable_issue=OuterRef("pk"),
        return_request__status=ReturnRequest.Status.PENDING,
    )

    pending_qty_subquery = (
        pending_items
        .values("consumable_issue")
        .annotate(total=Sum("quantity"))
        .values("total")
    )

    return (
        get_user_consumables(user)
        .select_related(
            "consumable",
            "consumable__room",
            "consumable__room__location",
        )
        .annotate(
            pending_return_quantity=Coalesce(
                Subquery(pending_qty_subquery[:1], output_field=IntegerField()),
                Value(0),
            ),
        )
        .annotate(
            has_pending_return_request=Exists(pending_items),
            available_return_quantity=Greatest(
                F("quantity") - F("pending_return_quantity"),
                Value(0),
            ),
        )
    )
def get_user_accessories(user):
    return AccessoryAssignment.objects.filter(
        user=user,
        returned_at__isnull=True,
        quantity__gt=0,
        accessory__is_deleted=False,
    )


def get_user_consumables(user):
    return ConsumableIssue.objects.filter(
        user=user,
        returned_at__isnull=True,
        quantity__gt=0,
        consumable__is_deleted=False,
    )

def equipment_active_q(viewer=None):

    q = Q(
        equipment_assignments__returned_at__isnull=True,
        equipment_assignments__equipment__is_deleted=False,
    )

    if viewer is None:
        return q

    role = getattr(viewer, "active_role", None)

    if not role:
        return q & Q(pk=None)

    if role.role == "SITE_ADMIN":
        return q

    if role.room:
        return q & Q(equipment_assignments__equipment__room=role.room)

    if role.location:
        return q & Q(equipment_assignments__equipment__room__location=role.location)

    if role.department:
        return q & Q(equipment_assignments__equipment__room__location__department=role.department)

    return q
    

def accessory_active_q(viewer=None):

    q = Q(
        accessory_assignments__returned_at__isnull=True,
        accessory_assignments__quantity__gt=0,
        accessory_assignments__accessory__is_deleted=False,
    )

    if viewer is None:
        return q

    role = getattr(viewer, "active_role", None)

    if not role:
        return q & Q(pk=None)

    if role.role == "SITE_ADMIN":
        return q

    if role.room:
        return q & Q(accessory_assignments__accessory__room=role.room)

    if role.location:
        return q & Q(accessory_assignments__accessory__room__location=role.location)

    if role.department:
        return q & Q(accessory_assignments__accessory__room__location__department=role.department)

    return q


def consumable_active_q(viewer=None):

    q = Q(
        consumable_assignments__returned_at__isnull=True,
        consumable_assignments__quantity__gt=0,
        consumable_assignments__consumable__is_deleted=False,
    )

    if viewer is None:
        return q

    role = getattr(viewer, "active_role", None)

    if not role:
        return q & Q(pk=None)

    if role.role == "SITE_ADMIN":
        return q

    if role.room:
        return q & Q(consumable_assignments__consumable__room=role.room)

    if role.location:
        return q & Q(consumable_assignments__consumable__room__location=role.location)

    if role.department:
        return q & Q(consumable_assignments__consumable__room__location__department=role.department)

    return q