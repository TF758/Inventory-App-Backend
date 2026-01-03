from db_inventory.models.audit import AuditLog
from django.utils.text import capfirst



def _resolve_scope_from_target(target):
    """
    Resolve department / location / room from the target object itself.
    """
    room = location = department = None
    room_name = location_name = department_name = None

    if not target:
        return {
            "room": None,
            "room_name": None,
            "location": None,
            "location_name": None,
            "department": None,
            "department_name": None,
        }

    if hasattr(target, "room") and target.room:
        room = target.room
        room_name = room.name

        if getattr(room, "location", None):
            location = room.location
            location_name = location.name

            if getattr(location, "department", None):
                department = location.department
                department_name = department.name

    elif hasattr(target, "location") and target.location:
        location = target.location
        location_name = location.name

        if getattr(location, "department", None):
            department = location.department
            department_name = department.name

    elif hasattr(target, "department") and target.department:
        department = target.department
        department_name = department.name

    return {
        "room": room,
        "room_name": room_name,
        "location": location,
        "location_name": location_name,
        "department": department,
        "department_name": department_name,
    }


def _get_target_label(target):
    if not target:
        return None

    if hasattr(target, "audit_label") and callable(target.audit_label):
        return target.audit_label()

    return str(target)


def _get_target_model(target):
    if not target:
        return None

    # Human-friendly, stable name
    return capfirst(target.__class__.__name__)



def diff_instance(instance, new_data):
    changes = {}
    for field, new_value in new_data.items():
        old_value = getattr(instance, field, None)
        if old_value != new_value:
            changes[field] = {
                "from": old_value,
                "to": new_value,
            }
    return changes


def create_audit_log(
    *,
    request,
    event_type,
    description="",
    target=None,
    metadata=None,
):
    """
    Create an immutable audit log entry.
    Intended for explicit domain actions (non-CRUD).
    """

    user = getattr(request, "user", None)
    scope = _resolve_scope_from_target(target)

    AuditLog.objects.create(
        # Actor
        user=user,
        user_public_id=getattr(user, "public_id", None),
        user_email=getattr(user, "email", None),

        # Event
        event_type=event_type,
        description=description,
        metadata=metadata or {},

        # Target snapshot
        target_model=_get_target_model(target),
        target_id=getattr(target, "public_id", None),
        target_name=_get_target_label(target),

        # Scope snapshot (derived from target)
        department=scope["department"],
        department_name=scope["department_name"],
        location=scope["location"],
        location_name=scope["location_name"],
        room=scope["room"],
        room_name=scope["room_name"],

        # Request context
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
