"""
Role-permission compatibility boundaries.

This module answers only:

    Can this role type ever be granted this permission code?

It does not answer:

    - Does the active role currently have this permission?
    - Is the object inside the active role's scope?
    - Can this actor govern a specific target role assignment?

Those checks belong to AccessService, ScopeService, and role governance.
"""

VIEWER_ROLES = {
    "ROOM_VIEWER",
    "LOCATION_VIEWER",
    "DEPARTMENT_VIEWER",
}

ROOM_ROLES = {
    "ROOM_VIEWER",
    "ROOM_CLERK",
    "ROOM_ADMIN",
}

LOCATION_ROLES = {
    "LOCATION_VIEWER",
    "LOCATION_ADMIN",
}

DEPARTMENT_ROLES = {
    "DEPARTMENT_VIEWER",
    "DEPARTMENT_ADMIN",
}

ADMIN_ROLES = {
    "ROOM_ADMIN",
    "LOCATION_ADMIN",
    "DEPARTMENT_ADMIN",
}

SYSTEM_ROLES = {
    "SITE_ADMIN",
}


# ------------------------------------------------------------------
# System / non-configurable authority
# ------------------------------------------------------------------

SITE_ADMIN_ONLY_EXACT_PERMISSIONS = {
    "auth.manage_permissions",
    "roles.manage_permissions",
    "permissions.view",

    # Global / dangerous actions
    "assets.hard_delete",
    "assignments.view_all",
    "reports.manage",

    # Security/session controls
    "sessions.view",
    "sessions.revoke",

    # Cross-user active role control
    "role_assignments.activate",

    # Unrestricted user creation, if different from scoped full_create.
    "users.create",
}


# ------------------------------------------------------------------
# Viewer-safe permissions
# ------------------------------------------------------------------

VIEWER_ALLOWED_PERMISSION_PREFIXES = {
    "reports.",
}

VIEWER_ALLOWED_PERMISSION_SUFFIXES = {
    ".view",
    ".self_view",
}

VIEWER_ALLOWED_EXACT_PERMISSIONS = {
    "returns.self_return",
    "returns.request_asset_return",
    "role_assignments.self_activate",
    "sessions.self_view",
    "sessions.self_revoke",
    "users.self_update",
}


# ------------------------------------------------------------------
# Clerk boundary
# ------------------------------------------------------------------

CLERK_BLOCKED_PREFIXES = {
    "departments.",
    "locations.",
    "role_assignments.",
    "user_placements.",
    "sessions.",
}

CLERK_BLOCKED_EXACT_PERMISSIONS = {
    "assets.delete",
    "assets.hard_delete",
    "assets.restore",
    "assets.condemn",

    "assignments.update",
    "assignments.unassign",
    "assignments.reassign",
    "assignments.view_all",

    "returns.process",
    "returns.delete",

    "users.create",
    "users.full_create",
    "users.update",
    "users.delete",
    "users.lock",
    "users.unlock",
    "users.manage",

    "rooms.create",
    "rooms.update",
    "rooms.transfer",
    "rooms.delete",
}


# ------------------------------------------------------------------
# Structural hierarchy boundaries
# ------------------------------------------------------------------

ROOM_ROLE_BLOCKED_PREFIXES = {
    "departments.",
    "locations.",
}

LOCATION_ROLE_BLOCKED_PREFIXES = {
    "departments.",
}

ROOM_ROLE_BLOCKED_EXACT_PERMISSIONS = {
    # A room role may view/update its own room if configured,
    # but should not create/delete/transfer rooms.
    "rooms.create",
    "rooms.transfer",
    "rooms.delete",
}

LOCATION_ROLE_BLOCKED_EXACT_PERMISSIONS = {
    # A location role may update its own location if configured,
    # and manage rooms under it if configured.
    # But creation/deletion/transfer of locations belongs higher.
    "locations.create",
    "locations.transfer",
    "locations.delete",
}


# ------------------------------------------------------------------
# Governance boundaries
# ------------------------------------------------------------------

ADMIN_ONLY_PREFIXES = {
    "user_placements.",
}

ADMIN_ONLY_EXACT_PERMISSIONS = {
    "role_assignments.create",
    "role_assignments.update",
    "role_assignments.delete",
    "role_assignments.manage",

    "users.full_create",
    "users.update",

    "returns.process",
}

DEPARTMENT_ADMIN_ONLY_EXACT_PERMISSIONS = {
    "agreements.create",
    "agreements.update",
    "agreements.delete",

    "users.delete",
    "users.lock",
    "users.unlock",

    "locations.create",
    "locations.transfer",
    "locations.delete",
}


def _starts_with_any(
    permission_code: str,
    prefixes: set[str],
) -> bool:
    return any(
        permission_code.startswith(prefix)
        for prefix in prefixes
    )


def _ends_with_any(
    permission_code: str,
    suffixes: set[str],
) -> bool:
    return any(
        permission_code.endswith(suffix)
        for suffix in suffixes
    )


def is_viewer_safe_permission(
    permission_code: str,
) -> bool:
    if not permission_code:
        return False

    if permission_code in VIEWER_ALLOWED_EXACT_PERMISSIONS:
        return True

    if _starts_with_any(
        permission_code,
        VIEWER_ALLOWED_PERMISSION_PREFIXES,
    ):
        return True

    return _ends_with_any(
        permission_code,
        VIEWER_ALLOWED_PERMISSION_SUFFIXES,
    )

def is_permission_allowed_for_role(
    role: str,
    permission_code: str,
) -> bool:
    """
    Return whether a role type may ever be granted a permission code.

    This does not check whether the role currently has the permission.
    This does not check object scope.
    This does not check role-assignment governance.
    """
    if not role or not permission_code:
        return False

    # SITE_ADMIN is system authority, but should normally be excluded
    # from the editable matrix upstream.
    if role in SYSTEM_ROLES:
        return True

    # System-only permissions cannot be granted to normal roles.
    if permission_code in SITE_ADMIN_ONLY_EXACT_PERMISSIONS:
        return False

    # --------------------------------------------------
    # Structural hierarchy boundaries
    # --------------------------------------------------
    # These must run before viewer-safe `.view` checks.
    # Otherwise ROOM_VIEWER would incorrectly receive
    # locations.view / departments.view.
    # --------------------------------------------------

    if role in ROOM_ROLES:
        if _starts_with_any(
            permission_code,
            ROOM_ROLE_BLOCKED_PREFIXES,
        ):
            return False

        if permission_code in ROOM_ROLE_BLOCKED_EXACT_PERMISSIONS:
            return False

    if role in LOCATION_ROLES:
        if _starts_with_any(
            permission_code,
            LOCATION_ROLE_BLOCKED_PREFIXES,
        ):
            return False

        if permission_code in LOCATION_ROLE_BLOCKED_EXACT_PERMISSIONS:
            return False

    # Viewers are always read/self/report only,
    # but only after their hierarchy level has been enforced.
    if role in VIEWER_ROLES:
        return is_viewer_safe_permission(permission_code)

    # Clerks are operational, not governance/structure/security.
    if role == "ROOM_CLERK":
        if permission_code in CLERK_BLOCKED_EXACT_PERMISSIONS:
            return False

        if _starts_with_any(
            permission_code,
            CLERK_BLOCKED_PREFIXES,
        ):
            return False

    # Admin/governance capabilities require admin-shaped roles.
    if permission_code in ADMIN_ONLY_EXACT_PERMISSIONS:
        return role in ADMIN_ROLES

    if _starts_with_any(
        permission_code,
        ADMIN_ONLY_PREFIXES,
    ):
        return role in ADMIN_ROLES

    # Department-level destructive / structural authority.
    if permission_code in DEPARTMENT_ADMIN_ONLY_EXACT_PERMISSIONS:
        return role == "DEPARTMENT_ADMIN"

    return True