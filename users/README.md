# Users — Authentication & Authorization

> Django app handling user management, authentication, roles, and permissions.

The `users` app provides the identity and access layer for ARMS, managing users, roles, and permission scoping.

---

## Overview

The users app handles all identity-related concerns — from authentication to role-based access control. It extends Django's auth system with custom user models, role assignments with scope (room, location, department), and active role switching.

This follows the **domain-driven design** pattern — all user and role-related concerns are encapsulated here.

---

## What Users Provides

### User Model

Custom user model extending Django's AbstractBaseUser:

```python
class User(AbstractBaseUser, PermissionsMixin, PublicIDModel):
    PUBLIC_ID_PREFIX = "USR"

    email = models.EmailField(blank=True, default='', unique=True, db_index=True)
    fname = models.CharField(max_length=30, blank=True, default='')
    lname = models.CharField(max_length=30, blank=True, default='')
    job_title = models.CharField(max_length=50, blank=True, default='')
    role = models.CharField(max_length=20, blank=True, default='user')

    active_role = models.ForeignKey("RoleAssignment", on_delete=models.SET_NULL, null=True, blank=True, related_name="active_for_users")

    created_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_users")
    is_locked = models.BooleanField(default=False)
    is_system_user = models.BooleanField(default=False)  # for test/demo/system accounts
    force_password_change = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
```

Features:

- Email as username (USERNAME_FIELD = 'email')
- Public ID with `USR` prefix
- First/last name and job title
- Role field (legacy, superseded by RoleAssignment)
- Active role switching via `active_role` foreign key
- Account locking (`is_locked`)
- System user flag for test/demo accounts
- Password change enforcement (`force_password_change`)

### Custom User Manager

```python
class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        # Validates email, normalizes, sets password

    def create_user(self, email=None, password=None, **extra_fields):
        # Regular user creation

    def create_superuser(self, email=None, password=None, **extra_fields):
        # Admin user creation
```

### RoleAssignment Model

Granular role assignments with scope:

```python
class RoleAssignment(PublicIDModel):
    PUBLIC_ID_PREFIX = "RA"

    ROLE_CHOICES = [
        # Room roles
        ("ROOM_VIEWER", "Room Viewer"),
        ("ROOM_CLERK", "Room Clerk"),
        ("ROOM_ADMIN", "Room Admin"),

        # Location roles
        ("LOCATION_VIEWER", "Location Viewer"),
        ("LOCATION_ADMIN", "Location Admin"),

        # Department roles
        ("DEPARTMENT_VIEWER", "Department Viewer"),
        ("DEPARTMENT_ADMIN", "Department Admin"),

        # Global
        ("SITE_ADMIN", "Site Admin"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.CharField(max_length=40, choices=ROLE_CHOICES)

    # Scope (only ONE may be set, depending on role)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)

    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_roles")
    assigned_date = models.DateTimeField(default=timezone.now)
```

Role hierarchy:

- **Room roles** — ROOM_VIEWER, ROOM_CLERK, ROOM_ADMIN (scope: specific room)
- **Location roles** — LOCATION_VIEWER, LOCATION_ADMIN (scope: specific location)
- **Department roles** — DEPARTMENT_VIEWER, DEPARTMENT_ADMIN (scope: specific department)
- **Global** — SITE_ADMIN (no scope needed)

---

## Architecture

```
users/
├── models/
│   ├── users.py   # User model, CustomUserManager
│   └── roles.py   # RoleAssignment model
├── api/
│   ├── serializers/    # DRF serializers
│   └── viewsets/       # API view sets
├── selectors/          # QuerySet builders
├── services/           # Business logic
├── tasks/              # Celery tasks
├── filters/            # Filter backends
├── factories/          # Test factories
├── tests/              # Unit tests
├── urls/               # URL routing
└── utils/              # Helper functions
```

---

## Key Patterns

### Active Role Switching

Users can switch between their assigned roles:

```python
# Set active role
user.active_role = role_assignment
user.save()

# Check permissions against active role
if user.active_role and user.active_role.role == 'ROOM_ADMIN':
    # Grant admin access
```

### Full Name Handling

```python
def get_full_name(self):
    parts = [self.fname, self.lname]
    return " ".join(p for p in parts if p).strip() or self.email

def get_short_name(self):
    return self.fname if self.fname else self.email.split('@')[0]
```

### Account Locking

```python
# Lock user account
user.is_locked = True
user.save()

# Check if locked
if user.is_locked:
    # Deny access
```

---

## Usage

### Creating Users

```python
from users.models import User

user = User.objects.create_user(
    email="john@example.com",
    password="securepassword",
    fname="John",
    lname="Doe",
    job_title="Developer"
)
# Generates public_id: USR-XXXXX
```

### Creating Superuser

```python
admin = User.objects.create_superuser(
    email="admin@example.com",
    password="adminpassword"
)
```

### Assigning Roles

```python
from users.models import RoleAssignment

# Assign room admin role
role = RoleAssignment.objects.create(
    user=user,
    role="ROOM_ADMIN",
    room=room,
    assigned_by=admin_user
)

# Set as active role
user.active_role = role
user.save()
```

### Querying Users

```python
# Get all active users
User.objects.filter(is_active=True, is_locked=False)

# Get users by role
User.objects.filter(role_assignments__role="SITE_ADMIN")

# Get user's role assignments
user.role_assignments.all()
```

---

## Dependencies

- **core** — PublicIDModel, base classes
- **sites** — Department, Location, Room models for role scope

---

## Authentication

The users app integrates with Django's auth system:

- JWT authentication via djangorestframework-simplejwt
- Session-based authentication for admin
- Password hashing with Django's password validators
- Login/logout endpoints at `/api/auth/login/`

---

## API Endpoints

Typical endpoints:

- `POST /api/auth/login/` — JWT login
- `POST /api/auth/logout/` — Logout
- `POST /api/auth/refresh/` — Refresh token
- `GET /api/users/` — List users
- `POST /api/users/` — Create user
- `GET /api/users/{public_id}/` — Get user
- `PATCH /api/users/{public_id}/` — Update user
- `POST /api/users/{public_id}/roles/` — Assign role
- `POST /api/users/{public_id}/switch-role/` — Switch active role

---

## Testing

Run user-specific tests:

```bash
python manage.py test users
```

---

## Related Documentation

- [Core Models](../core/README.md)
- [Assets](../assets/README.md)
- [Assignments](../assignments/README.md)
- [Sites](../sites/README.md)
- [API Overview](../README.md)
