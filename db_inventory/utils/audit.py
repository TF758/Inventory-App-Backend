from db_inventory.models.audit import AuditLog


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
    user = request.user
    role = getattr(user, "active_role", None)

    AuditLog.objects.create(
        user=user,
        user_public_id=getattr(user, "public_id", None),
        user_email=getattr(user, "email", None),

        event_type=event_type,
        description=description,
        metadata=metadata or {},

        target_model=target.__class__.__name__ if target else None,
        target_id=getattr(target, "public_id", None),
        target_name=str(target) if target else None,

        department=getattr(role, "department", None),
        department_name=getattr(role.department, "name", None) if role and role.department else None,

        location=getattr(role, "location", None),
        location_name=getattr(role.location, "name", None) if role and role.location else None,

        room=getattr(role, "room", None),
        room_name=getattr(role.room, "name", None) if role and role.room else None,

        ip_address=getattr(request, "META", {}).get("REMOTE_ADDR"),
        user_agent=getattr(request, "META", {}).get("HTTP_USER_AGENT"),
    )