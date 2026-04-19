
from db_inventory.models.audit import AuditLog
from db_inventory.permissions.helpers import can_hard_delete_asset, can_soft_delete_asset
from db_inventory.utils.asset_helpers import ASSET_CONFIG
from django.db import transaction
from django.utils import timezone

from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment
from assignments.services.equipment_assignment import StatusChangeResult

def create_asset_audit_log(
    *,
    actor,
    asset,
    event_type,
    description,
    metadata=None,
):
    room = getattr(asset, "room", None)
    location = getattr(room, "location", None) if room else None
    department = getattr(location, "department", None) if location else None

    AuditLog.objects.create(
        user=actor,
        user_public_id=actor.public_id,
        user_email=actor.email,
        event_type=event_type,
        description=description,
        metadata=metadata or {},
        target_model=asset.__class__.__name__,
        target_id=asset.public_id,
        target_name=asset.audit_label(),
        room=room,
        room_name=room.name if room else None,
        location=location,
        location_name=location.name if location else None,
        department=department,
        department_name=department.name if department else None,
    )

def soft_delete_asset(
    *,
    actor,
    asset,
    notes="",
    batch=False,
    now=None,
    use_atomic=True,
    lock_asset=True,
):
    """
    Generic soft delete for room-scoped assets.

    Supports Equipment, Accessory, Consumable, etc.
    """

    if now is None:
        now = timezone.now()

    def _execute():

        obj = asset

        # --- Optional row locking ---
        if lock_asset:
            obj = (
                type(asset).objects
                .select_for_update()
                .get(pk=asset.pk)
            )

        # --- Skip if already deleted ---
        if getattr(obj, "is_deleted", False):
            return StatusChangeResult.SKIPPED

        # --- Permission guard ---
        if not can_soft_delete_asset(actor, obj):
            raise PermissionError("Not allowed to delete asset.")

        # --- Soft delete ---
        obj.is_deleted = True
        obj.deleted_at = now
        obj.save(update_fields=["is_deleted", "deleted_at"])

        # --- Audit log (via helper) ---
        create_asset_audit_log(
            actor=actor,
            asset=obj,
            event_type=AuditLog.Events.MODEL_DELETED,
            description=f"{obj.__class__.__name__} soft deleted",
            metadata={
                "change_type": "asset_soft_deleted",
                "notes": notes,
                "batch": batch,
            },
        )

        return StatusChangeResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()

    return _execute()

def hard_delete_asset(
    *,
    actor,
    asset,
    notes="",
    batch=False,
    now=None,
    use_atomic=True,
    lock_asset=True,
):
    """
    Generic permanent delete for assets.
    SITE_ADMIN only (handled inside can_hard_delete_asset).
    """

    if now is None:
        now = timezone.now()

    def _execute():

        obj = asset

        # --- Optional row locking ---
        if lock_asset:
            obj = (
                type(asset).objects
                .select_for_update()
                .get(pk=asset.pk)
            )

        # --- Permission guard ---
        if not can_hard_delete_asset(actor, obj):
            raise PermissionError("Not allowed to permanently delete asset.")

        # --- Audit BEFORE deletion ---
        create_asset_audit_log(
            actor=actor,
            asset=obj,
            event_type=AuditLog.Events.MODEL_PERMANENTLY_DELETED,
            description=f"{obj.__class__.__name__} permanently deleted",
            metadata={
                "change_type": "asset_hard_deleted",
                "notes": notes,
                "batch": batch,
            },
        )

        # --- HARD DELETE ---
        obj.delete()

        return StatusChangeResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()

    return _execute()

def restore_asset(
    *,
    actor,
    asset,
    batch=False,
    now=None,
    use_atomic=True,
    lock_asset=True,
):
    """
    Generic restore for soft-deleted assets.

    Works for Equipment, Accessory, Consumable, etc.
    """

    if now is None:
        now = timezone.now()

    def _execute():

        obj = asset

        # --- Optional locking ---
        if lock_asset:
            obj = (
                type(asset).objects
                .select_for_update()
                .get(pk=asset.pk)
            )

        # --- Skip if not deleted ---
        if not getattr(obj, "is_deleted", False):
            return StatusChangeResult.SKIPPED

        # --- Permission guard ---
        # Restore follows same rule as soft delete
        if not can_soft_delete_asset(actor, obj):
            raise PermissionError("Not allowed to restore asset.")

        # --- Restore state ---
        obj.is_deleted = False
        obj.deleted_at = None
        obj.save(update_fields=["is_deleted", "deleted_at"])

        # --- Audit log via helper ---
        create_asset_audit_log(
            actor=actor,
            asset=obj,
            event_type=AuditLog.Events.ASSET_RESTORED,
            description=f"{obj.__class__.__name__} restored from soft delete",
            metadata={
                "change_type": "asset_restored",
                "batch": batch,
            },
        )

        return StatusChangeResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()

    return _execute()


def get_user_active_assets(user):

    equipment = EquipmentAssignment.objects.filter(
        user=user,
        returned_at__isnull=True,
        equipment__is_deleted=False,
    )

    accessories = AccessoryAssignment.objects.filter(
        user=user,
        returned_at__isnull=True,
        accessory__is_deleted=False,
    )

    consumables = ConsumableIssue.objects.filter(
        user=user,
        returned_at__isnull=True,
        consumable__is_deleted=False,
    )

    return {
        "equipment": equipment,
        "accessories": accessories,
        "consumables": consumables,
    }


def user_has_active_assets(user):
    assets = get_user_active_assets(user)

    return (
        assets["equipment"].exists()
        or assets["accessories"].exists()
        or assets["consumables"].exists()
    )