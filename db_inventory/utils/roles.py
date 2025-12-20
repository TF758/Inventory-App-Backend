def user_can_access_role(user, role_obj):
    """
    Checks if the user's active_role allows read access to the given RoleAssignment.
    """
    active = getattr(user, "active_role", None)
    if not active:
        return False

    if isinstance(active, dict):
        active_role_name = active.get("role")
        active_dep = active.get("department")
        active_loc = active.get("location")
        active_room = active.get("room")
    else:
        active_role_name = getattr(active, "role", None)
        active_dep = getattr(active, "department", None)
        active_loc = getattr(active, "location", None)
        active_room = getattr(active, "room", None)

    if user.is_superuser or active_role_name == "SITE_ADMIN":
        return True

    # Read-only scoping for department
    if active_role_name == "DEPARTMENT_ADMIN":
        return (
            role_obj.department == active_dep
            or (role_obj.location and role_obj.location.department == active_dep)
            or (role_obj.room and role_obj.room.location.department == active_dep)
        )

    # Location scoping
    if active_role_name == "LOCATION_ADMIN":
        role_location = role_obj.location or getattr(role_obj.room, "location", None)
        return role_location == active_loc

    # Room scoping
    if active_role_name == "ROOM_ADMIN":
        return role_obj.room == active_room

    # Viewer/clerk roles can only see their room
    if active_role_name in ["ROOM_VIEWER", "ROOM_CLERK"]:
        return role_obj.room == active_room

    return False
