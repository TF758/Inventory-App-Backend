# Access Module

> Documentation for the permission and role-access layer of the inventory system.

The access module is responsible for defining, validating, and enforcing permissions across the application. It connects the business rules of the domain apps with the authentication layer, so that each endpoint, action, and object access check is evaluated through a consistent permission model.

---

## Overview

The access module is built around three core ideas:

1. A permission catalog
   - Permissions are stored as records in the Permission model.
   - Each permission has a code such as `assets.view`, `users.create`, or `reports.manage`.

2. Role-to-permission grants
   - RolePermission links a role to a permission.
   - This is the main runtime source for what a role is allowed to do.

3. Policy and scope checks
   - Permission boundaries prevent invalid combinations.
   - Scope services ensure that a role can only act within its assigned hierarchy level.

This makes access management both centralized and configurable.

---

## Main responsibilities

The module does four important things:

- Defines the permission model and role-permission mapping
- Enforces permission checks for API endpoints and views
- Applies role-based boundaries so some permissions are reserved or restricted
- Exposes runtime permission data to the frontend so UI elements can be gated correctly

---

## Core files and their purpose

### Models

- [access/models.py](models.py)
  - Defines `Permission` and `RolePermission`
  - `Permission` stores the permission definition
  - `RolePermission` links a role to a specific permission

### Services

- [access/services/access.py](services/access.py)
  - `AccessService.has_permission(user, permission_code)` checks whether the active role has a given permission

- [access/services/permissions.py](services/permissions.py)
  - `PermissionMatrixService` reads and updates the configurable permission matrix
  - Used by the permission management UI

- [access/services/runtime_permissions.py](services/runtime_permissions.py)
  - Builds the runtime permission payload for the currently active role
  - Used by the frontend permission context

- [access/services/scope.py](services/scope.py)
  - Resolves hierarchy scope such as department, location, or room access
  - Used to decide whether a role can act on a specific object

### Policy and boundary logic

- [access/role_permission_boundaries.py](role_permission_boundaries.py)
  - Central policy layer for role-permission compatibility
  - Prevents invalid grants such as assigning a viewer-only permission to an admin role or giving room-scoped permissions to a department role
  - Includes helpers such as `get_permission_boundary_result()` and `is_permission_allowed_for_role()`

### Permission enforcement classes

- [access/permissions/base.py](permissions/base.py)
  - `RequiresPermission` is the reusable DRF permission class for endpoint-level checks

- [access/permissions/site_admin.py](permissions/site_admin.py)
  - `IsActiveSiteAdmin` ensures only an active Site Admin can access permission-management endpoints

- [access/permissions/](permissions/)
  - Domain-specific permission classes such as assets, users, assignments, returns, and sites
  - These classes connect endpoint actions to permission codes and object-level rules

### API and matrix management

- [access/views.py](views.py)
  - `PermissionMatrixView` exposes the permission matrix for management
  - `SelfPermissionsView` returns the runtime permission list for the current user role

- [access/serialziers.py](serialziers.py)
  - Validates payloads sent when updating the permission matrix
  - Checks duplicate entries and enforces role-permission boundary rules

- [access/urls.py](urls.py)
  - Registers the permission matrix endpoint

---

## How permissions are created and attached

The module does not rely on a single “magic” permission factory. Instead, permission creation is a data-driven flow:

### 1. Create a permission record

A permission is usually created as a `Permission` object with:

- `domain` such as `assets`, `users`, `reports`
- `code` such as `assets.view` or `users.full_create`
- `name`
- `description`
- `scope_type`
- `is_configurable`

Permissions can be created through Django data setup, fixtures, migrations, or a seed process.

### 2. Decide whether the permission is configurable

The `is_configurable` flag controls whether the permission can be edited through the matrix UI.

- `True` means the permission can be granted or revoked through the permission matrix
- `False` means it is reserved for system-level or special-case authority

Examples of non-configurable permissions include system-admin-only or security-related permissions.

### 3. Grant the permission to one or more roles

Once the permission exists, it is linked to roles via `RolePermission`.

This can happen in two ways:

- Through the permission matrix UI, which updates the `RolePermission` rows
- Through a bulk seed script, such as [access/management/commands/seed_role_permissions.py](management/commands/seed_role_permissions.py)

The seed command reads a spreadsheet and creates `RolePermission` entries based on the permission code and role columns.

### 4. Enforce the permission at runtime

When a request comes in, the permission check is resolved through the access service and the relevant permission class. If the user’s active role does not have the required permission, the request is denied.

---

## How permission checks work

The request flow is usually:

1. The view or API endpoint declares one or more required permissions
2. The DRF permission class resolves those requirements
3. `AccessService.has_permission()` checks the active role against `RolePermission`
4. If allowed, the request continues; otherwise a permission error is raised

A typical pattern looks like this:

```python
class ExampleView(APIView):
    permission_classes = [RequiresPermission]

    required_permission = "assets.view"
```

---

## Permission boundaries and safety rules

The module includes a policy layer to prevent unsafe or invalid role-permission combinations.

Examples of boundaries:

- Viewer roles are limited to read/self-service access
- Clerk roles cannot receive destructive or administrative permissions
- Room-based roles cannot receive department-level structure permissions
- Some permissions are reserved only for Site Admin

These rules are implemented in [access/role_permission_boundaries.py](role_permission_boundaries.py) and are enforced when updating the permission matrix.

---

## Runtime permission integration

The frontend relies on runtime permissions for UI gating. The flow is:

- `RuntimePermissionService.get_for_user(user)` gathers permissions for the active role
- The service returns the active role payload plus the list of permission codes
- The frontend uses this information to enable or disable screens, buttons, and actions

This is separate from the editable permission matrix and is intended for runtime presentation only.

---

## Helper classes and utilities

Here is a brief summary of the main helpers:

- `RequiresPermission`
  - Checks whether the current user has one or more required permissions

- `IsActiveSiteAdmin`
  - Restricts permission-management actions to active Site Admin users

- `AccessService`
  - Performs the core permission lookup against the current role

- `PermissionMatrixService`
  - Reads and updates the admin-configurable permission matrix

- `RuntimePermissionService`
  - Builds the permission payload for the frontend

- `ScopeService`
  - Resolves whether a role can act on a specific hierarchical scope such as a room or location

- Boundary helpers
  - Enforce authorization policy and role compatibility rules

---

## Typical workflow for adding a new permission

When a new feature needs a permission, the usual flow is:

1. Define a new permission code in the permission catalog
2. Mark it configurable if it should be managed through the matrix
3. Add the permission to the relevant view or action class
4. Grant it to the necessary roles in the matrix or seed data
5. Verify that the frontend and backend both reflect the new access rule

A good permission code usually follows a consistent pattern such as:

- `module.action`
- `module.object_action`
- `module.self_action`

Examples:

- `assets.view`
- `users.create`
- `returns.process`

---

## Notes for maintainers

- Keep permission codes consistent and predictable
- Prefer explicit, domain-based naming over generic names
- Use the boundary policy to prevent impossible or unsafe grants
- Treat the permission matrix as the main administrative control surface for role access
- Keep endpoint-level permission requirements close to the view logic so access changes are easy to audit

---

## Summary

The access module is the authorization backbone of the system. It centralizes permissions, enforces them consistently, protects the permission-management workflow, and provides runtime permission data for the UI. Its design is based on a clean separation between:

- permission definitions
- role assignments
- policy boundaries
- runtime enforcement

That separation makes the system easier to maintain and safer to extend.
