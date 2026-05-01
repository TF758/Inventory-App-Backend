# Core Tests — Coverage Overview

> Quick reference for developers to understand what's tested in the core module.

---

## Test Files Summary

| Test File                                      | What Is Covered                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------------------- |
| `test_login_refresh.py`                        | Login session creation, cookie handling, concurrent device logins, token refresh |
| `test_logout.py`                               | Session revocation, cookie clearing on logout                                    |
| `test_session_security.py`                     | Session limits (max concurrent), session expiry, cookie security                 |
| `test_user_password_reset.py`                  | Password reset request, email trigger, token validation, cooldown enforcement    |
| `test_public_id_generation.py`                 | ID generation on save, registry entry creation, manual ID respect, bulk_create   |
| `test_public_id_stress_test.py`                | Large dataset bulk inserts, high concurrency ID generation, manual ID handling   |
| `test_audit_logs.py`                           | Audit log creation on equipment create, event types, scope hierarchy             |
| `test_asset_lifecycle.py`                      | Soft delete, hard delete, restore operations for assets                          |
| `test_asset_agreement.py`                      | Asset agreement permissions (ROOM_ADMIN view/create)                             |
| `test_eq_batch_actions.py`                     | Batch equipment status changes, success/failure handling                         |
| `permissions/test_user_permissions.py`         | SITE_ADMIN user access, DEPARTMENT_ADMIN scope                                   |
| `permissions/test_asset_permissions.py`        | Equipment, accessory, consumable permission matrix                               |
| `permissions/test_userlocation_permissions.py` | User placement permission matrix                                                 |
| `permissions/test_role_assignments.py`         | Role assignment creation, role escalation prevention                             |
| `permissions/test_global_permissions.py`       | Role hierarchy, SITE_ADMIN bypass, scope helpers                                 |
| `permissions/test_room_level_scope.py`         | ROOM_ADMIN/ROOM_VIEWER scope enforcement                                         |
| `permissions/test_location_level_scope.py`     | LOCATION_ADMIN/LOCATION_VIEWER scope enforcement                                 |
| `permissions/test_department_level_scope.py`   | DEPARTMENT_ADMIN/DEPARTMENT_VIEWER scope enforcement                             |

---

## Coverage by Area

### Authentication & Sessions

- ✅ **Login** — Session creation, cookie setting, concurrent device handling
- ✅ **Token Refresh** — JWT refresh workflow, session continuity
- ✅ **Logout** — Session revocation, cookie clearing
- ✅ **Session Security** — Max concurrent sessions, absolute lifetime, idle timeout
- ✅ **Password Reset** — Reset flow, token validation, cooldown enforcement

### PublicID System

- ✅ **ID Generation** — Auto-generation on save, prefix handling (EQ, AC, CON, etc.)
- ✅ **Registry** — Entry creation, uniqueness enforcement
- ✅ **Manual IDs** — Respected on save, not overwritten
- ✅ **Bulk Operations** — bulk_create generates IDs for all records
- ✅ **Stress Testing** — 5000+ records, 20-thread concurrency

### Audit & Compliance

- ✅ **Equipment Creation** — Audit log created on model create
- ✅ **Event Types** — MODEL_CREATED captured
- ✅ **Scope Hierarchy** — Room → Location → Department preserved

### Asset Operations

- ✅ **Batch Status Change** — Multiple equipment status updates in one call
- ✅ **Lifecycle** — Soft delete, hard delete, restore
- ✅ **Agreements** — Asset agreement permissions

### Permissions & Roles

- ✅ **Role Hierarchy** — ROOM_ADMIN > ROOM_VIEWER, LOCATION_ADMIN > ROOM_ADMIN, etc.
- ✅ **Scope Enforcement** — Global, department, location, room-level access
- ✅ **SITE_ADMIN Bypass** — Full access regardless of scope
- ✅ **Asset Permissions** — Equipment, accessory, consumable CRUD
- ✅ **User Permissions** — User list/detail access by role
- ✅ **User Placement** — User location assignment permissions
- ✅ **Role Escalation** — Cannot assign higher roles than own

---

## Test Utilities

| File                              | Purpose                               |
| --------------------------------- | ------------------------------------- |
| `utils/_role_permissions_base.py` | Base class for role permission tests  |
| `utils/_asset_permission_base.py` | Base class for asset permission tests |
| `utils/userlocation_test_base.py` | Base class for user location tests    |

---

## Potential Future Coverage

- **JWT Blacklisting** — Token invalidation after logout
- **Audit Events** — MODEL_UPDATED, MODEL_DELETED, assignment events
- **Audit Immutability** — Logs cannot be modified after creation
- **Permission Inheritance** — Room → Location → Department hierarchy
- **Assignment Operations** — Asset assignment/reassignment tests

---

## Running Tests

```bash
# Run all core tests
python manage.py test core

# Run specific test file
python manage.py test core.tests.test_login_refresh

# Run with coverage
coverage run --manage.py test core
coverage report --include="core/*"
```

---

## Related Documentation

- [Reporting Tests](TEST_COVERAGE.md) — Reporting module test coverage
- [Local Setup](local_setup.md) — Running tests locally
