from django.db import transaction
from django.utils import timezone
from db_inventory.models import Equipment, EquipmentEvent
from db_inventory.permissions import CanManageAssetCustody
from db_inventory.models.audit import AuditLog
from db_inventory.models.security import Notification
from django.apps import apps
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from db_inventory.models.assets import EquipmentStatus
from db_inventory.permissions.helpers import can_hard_delete_asset, can_soft_delete_asset, is_admin_role, is_in_scope
from db_inventory.utils.asset_helpers import equipment_event_from_status

class UnassignResult:
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"

class AssignResult:
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"

def unassign_equipment(
    *,
    actor,
    equipment,
    notes="",
    now=None,
    use_atomic=True,
    lock_equipment=True,
):

    EquipmentAssignment = apps.get_model("db_inventory", "EquipmentAssignment")

    if now is None:
        now = timezone.now()

    def _execute():

        eq = equipment

        # ⭐ Only lock when requested
        if lock_equipment:
            eq = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

        assignment = (
            EquipmentAssignment.objects
            .select_for_update()
            .filter(equipment=eq, returned_at__isnull=True)
            .select_related("user")
            .first()
        )

        if not assignment:
            return UnassignResult.SKIPPED

        user = assignment.user

        assignment.returned_at = now
        assignment.save(update_fields=["returned_at"])

        EquipmentEvent.objects.create(
            equipment=eq,
            user=user,
            event_type=EquipmentEvent.Event_Choices.RETURNED,
            reported_by=actor,
            notes=notes or "Equipment returned",
        )

        AuditLog.objects.create(
            user=actor,
            user_public_id=actor.public_id,
            user_email=actor.email,
            event_type=AuditLog.Events.ASSET_UNASSIGNED,
            description=f"Unassigned from user {user.email}",
            metadata={
                "unassigned_from_public_id": user.public_id,
                "unassigned_from_email": user.email,
                "notes": notes,
            },
            target_model="Equipment",
            target_id=eq.public_id,
            target_name=eq.audit_label(),
        )

        channel_layer = get_channel_layer()

        def _send_notification(user, notif_type, level, title, message):
            notification = Notification.objects.create(
                recipient=user,
                type=notif_type,
                level=level,
                title=title,
                message=message,
                entity_type="equipment",
                entity_id=eq.public_id,
                meta=None,
            )

            payload = {
                "public_id": notification.public_id,
                "type": notification.type,
                "level": notification.level,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "entity": {
                    "type": notification.entity_type,
                    "id": notification.entity_id,
                },
                "meta": notification.meta,
            }

            async_to_sync(channel_layer.group_send)(
                f"user_{user.public_id}",
                {"type": "notification", "payload": payload},
            )


        def _notify():
            _send_notification(
                user,
                Notification.NotificationType.ASSET_ASSIGNED,  # adjust if you add UNASSIGNED type later
                Notification.Level.WARNING,
                "Equipment returned",
                f"{eq.name} has been unassigned from you by {actor.get_full_name()}.",
            )

            if actor != user:
                _send_notification(
                    actor,
                    Notification.NotificationType.ASSET_ASSIGNED,
                    Notification.Level.INFO,
                    "Equipment successfully unassigned",
                    f"You unassigned {eq.name} from {user.get_full_name()}.",
                )

        transaction.on_commit(_notify)



        return UnassignResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()
    else:
        return _execute()
    
def assign_equipment(
    *,
    actor,
    equipment,
    to_user,
    notes="",
    now=None,
    use_atomic=True,
    lock_equipment=True,
):

    EquipmentAssignment = apps.get_model("db_inventory", "EquipmentAssignment")

    if now is None:
        now = timezone.now()

    def _execute():

        eq = equipment

        if lock_equipment:
            eq = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

        assignment = (
            EquipmentAssignment.objects
            .select_for_update()
            .filter(equipment=eq, returned_at__isnull=True)
            .first()
        )

        # Already assigned → batch-safe skip
        if assignment:
            return AssignResult.SKIPPED

        assignment, _ = EquipmentAssignment.objects.get_or_create(
            equipment=eq,
            defaults={
                "user": to_user,
                "assigned_by": actor,
                "notes": notes,
            },
        )

        assignment.user = to_user
        assignment.assigned_by = actor
        assignment.assigned_at = now
        assignment.returned_at = None
        assignment.notes = notes
        assignment.save()

        EquipmentEvent.objects.create(
            equipment=eq,
            user=to_user,
            event_type=EquipmentEvent.Event_Choices.ASSIGNED,
            reported_by=actor,
            notes=notes or "Equipment assigned",
        )

        AuditLog.objects.create(
            user=actor,
            user_public_id=actor.public_id,
            user_email=actor.email,
            event_type=AuditLog.Events.ASSET_ASSIGNED,
            description=f"Assigned to user {to_user.email}",
            metadata={
                "assigned_to_public_id": to_user.public_id,
                "notes": notes,
            },
            target_model="Equipment",
            target_id=eq.public_id,
            target_name=eq.audit_label(),
        )

        channel_layer = get_channel_layer()

        def _notify():
            notification = Notification.objects.create(
                recipient=to_user,
                type=Notification.NotificationType.ASSET_ASSIGNED,
                level=Notification.Level.INFO,
                title="Equipment assigned to you",
                message=f"{eq.name} has been assigned to you by {actor.get_full_name()}.",
                entity_type="equipment",
                entity_id=eq.public_id,
                meta=None,
            )

            payload = {
                "public_id": notification.public_id,
                "type": notification.type,
                "level": notification.level,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "entity": {
                    "type": notification.entity_type,
                    "id": notification.entity_id,
                },
                "meta": notification.meta,
            }

            async_to_sync(channel_layer.group_send)(
                f"user_{to_user.public_id}",
                {"type": "notification", "payload": payload},
            )

        transaction.on_commit(_notify)

        return AssignResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()
    else:
        return _execute()
    

class StatusChangeResult:
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


def can_user_set_equipment_status(*, actor, equipment, new_status) -> bool:
    active_role = getattr(actor, "active_role", None)

    # SITE_ADMIN unrestricted
    if active_role and active_role.role == "SITE_ADMIN":
        return True

    # Scoped admin unrestricted (in scope)
    if (
        active_role
        and is_admin_role(active_role.role)
        and is_in_scope(active_role, room=getattr(equipment, "room", None))
    ):
        return True

    # Assigned user limited self-reporting
    assignment = getattr(equipment, "active_assignment", None)
    if assignment and assignment.returned_at is None and assignment.user_id == actor.id:
        allowed = {EquipmentStatus.OK, EquipmentStatus.DAMAGED, EquipmentStatus.UNDER_REPAIR}
        return new_status in allowed

    return False


def change_equipment_status(
    *,
    actor,
    equipment,
    new_status,
    notes="",
    now=None,
    use_atomic=True,
    lock_equipment=True,
):

    if now is None:
        now = timezone.now()

    EquipmentAssignment = apps.get_model("db_inventory", "EquipmentAssignment")

    def _execute():

        eq = equipment

        if lock_equipment:
            eq = Equipment.objects.select_for_update().get(pk=equipment.pk)

        old_status = eq.status

        if old_status == new_status:
            return StatusChangeResult.SKIPPED

        # safer assignment fetch (batch friendly)
        assignment = (
            EquipmentAssignment.objects
            .filter(equipment=eq, returned_at__isnull=True)
            .only("user_id")
            .first()
        )

        if not can_user_set_equipment_status(
            actor=actor,
            equipment=eq,
            new_status=new_status,
        ):
            raise PermissionError("Not allowed to set this status.")

        eq.status = new_status
        eq.save(update_fields=["status"])

        event_type = equipment_event_from_status(new_status)

        EquipmentEvent.objects.create(
            equipment=eq,
            user=actor,
            reported_by=actor,
            event_type=event_type,
            notes=notes or f"{old_status} → {new_status}",
        )

        AuditLog.objects.create(
            user=actor,
            user_public_id=actor.public_id,
            user_email=actor.email,
            event_type=AuditLog.Events.EQUIPMENT_STATUS_CHANGED,
            description=f"Status changed from {old_status} to {new_status}",
            metadata={
                "change_type": "equipment_status_change",
                "old_status": old_status,
                "new_status": new_status,
                "notes": notes,
                "batch": True,
            },
            target_model="Equipment",
            target_id=eq.public_id,
            target_name=eq.audit_label(),
        )

        return StatusChangeResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()
    return _execute()


def condemn_equipment(
    *,
    actor,
    equipment,
    notes="",
    now=None,
    use_atomic=True,
    lock_equipment=True,
):

    if now is None:
        now = timezone.now()

    EquipmentAssignment = apps.get_model("db_inventory", "EquipmentAssignment")

    def _execute():

        eq = equipment

        # Optional row locking (disabled in batch view because rows are already locked)
        if lock_equipment:
            eq = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

        old_status = eq.status
        new_status = EquipmentStatus.CONDEMNED

        # --- Skip if already condemned ---
        if old_status == new_status:
            return StatusChangeResult.SKIPPED

        # --- Permission guard ---
        if not can_user_set_equipment_status(
            actor=actor,
            equipment=eq,
            new_status=new_status,
        ):
            raise PermissionError("Not allowed to condemn equipment.")

        # --- State change ---
        eq.status = new_status
        eq.save(update_fields=["status"])

        # --- Domain event ---
        EquipmentEvent.objects.create(
            equipment=eq,
            user=actor,
            reported_by=actor,
            event_type=equipment_event_from_status(new_status),
            notes=notes or f"{old_status} → CONDEMNED",
        )

        # --- Audit trail ---
        AuditLog.objects.create(
            user=actor,
            user_public_id=actor.public_id,
            user_email=actor.email,
            event_type=AuditLog.Events.EQUIPMENT_STATUS_CHANGED,
            description=f"Equipment condemned (previous status: {old_status})",
            metadata={
                "change_type": "equipment_condemned",
                "old_status": old_status,
                "new_status": new_status,
                "notes": notes,
                "batch": True,
            },
            target_model="Equipment",
            target_id=eq.public_id,
            target_name=eq.audit_label(),
        )

        return StatusChangeResult.SUCCESS


    if use_atomic:
        with transaction.atomic():
            return _execute()

    # Used by batch views already running inside a transaction
    return _execute()

def soft_delete_equipment(
    *,
    actor,
    equipment,
    notes="",
    now=None,
    use_atomic=True,
    lock_equipment=True,
):

    if now is None:
        now = timezone.now()

    def _execute():

        eq = equipment

        # --- Optional row locking ---
        if lock_equipment:
            eq = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

        # --- Skip if already deleted ---
        if eq.is_deleted:
            return StatusChangeResult.SKIPPED

        # --- Permission guard ---
        if not can_soft_delete_asset(actor, eq):
            raise PermissionError("Not allowed to delete equipment.")

        # --- Soft delete ---
        eq.is_deleted = True
        eq.deleted_at = now
        eq.save(update_fields=["is_deleted", "deleted_at"])

        # --- Audit trail ---
        AuditLog.objects.create(
            user=actor,
            user_public_id=actor.public_id,
            user_email=actor.email,
            event_type=AuditLog.Events.MODEL_DELETED,
            description="Equipment soft deleted",
            metadata={
                "change_type": "equipment_soft_deleted",
                "notes": notes,
                "batch": True,
            },
            target_model="Equipment",
            target_id=eq.public_id,
            target_name=eq.audit_label(),
        )

        return StatusChangeResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()

    return _execute()

def hard_delete_equipment(
    *,
    actor,
    equipment,
    notes="",
    now=None,
    use_atomic=True,
    lock_equipment=True,
):

    if now is None:
        now = timezone.now()

    def _execute():

        eq = equipment

        # --- Optional locking ---
        if lock_equipment:
            eq = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

        # --- Permission guard ---
        if not can_hard_delete_asset(actor):
            raise PermissionError("Not allowed to permanently delete equipment.")

        # --- Audit BEFORE deletion ---
        AuditLog.objects.create(
            user=actor,
            user_public_id=actor.public_id,
            user_email=actor.email,
            event_type=AuditLog.Events.EQUIPMENT_PERMANENTLY_DELETED,
            description="Equipment permanently deleted",
            metadata={
                "change_type": "equipment_hard_deleted",
                "notes": notes,
                "batch": True,
            },
            target_model="Equipment",
            target_id=eq.public_id,
            target_name=eq.audit_label(),
        )

        # --- HARD DELETE ---
        eq.delete()

        return StatusChangeResult.SUCCESS

    if use_atomic:
        with transaction.atomic():
            return _execute()

    return _execute()