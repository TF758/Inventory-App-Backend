# Core — Shared Infrastructure & Cross-Cutting Concerns

> Central Django app providing foundational services, utilities, and shared components used across all domain modules.

The `core` app serves as the backbone of the ARMS platform, encapsulating cross-cutting concerns that every other app depends on.

---

## Overview

The core app provides the foundational layer that enables the entire system to function. It handles authentication, authorization, data patterns, caching, messaging, and infrastructure concerns that would otherwise be duplicated across domain apps.

This follows the **shared kernel** pattern — every other app imports from `core` for common functionality.

---

## What Core Provides

### Authentication & Sessions

- JWT-based token authentication
- Session management with revocation capabilities
- Token refresh workflows
- Password reset event tracking

### Data Models

- `PublicIDModel` — Base model providing unique, human-readable public IDs for all entities
- `SecuritySettings` — Global security configuration
- `AuditLog` — Immutable audit trail for critical actions
- `UserSession` — Active session tracking with revocation support
- `Notification` — System-wide notification storage
- `ScheduledTaskRun` — Track Celery task executions

### Permissions & Security

- Role-based access control (RBAC)
- Active role switching for users
- Permission classes for API views
- Security policy enforcement
- Throttling and rate limiting

### Infrastructure

- Redis connection management
- WebSocket consumers for real-time features
- Custom pagination classes
- Filter backends for querysets

### Utilities

- Ministry data helpers
- Mixins for common model/view behavior
- Serializer base classes
- ViewSet base classes

---

## Architecture

```
core/
├── admin.py           # Admin configuration
├── api_urls.py        # Core API route definitions
├── authentication.py  # JWT & session auth backends
├── consumers.py       # WebSocket consumers
├── filters.py         # Shared filter backends
├── mixins.py          # Reusable model/view mixins
├── pagination.py      # Custom paginators
├── redis.py           # Redis client utilities
├── routing.py         # WebSocket routing
├── security_policy.py # Security settings & enforcement
├── throttling.py      # Rate limiting classes
├── models/            # Core domain models
├── permissions/       # Permission classes
├── serializers/       # Base serializers
├── viewsets/          # Base viewsets
├── notifications/     # Notification system
├── utils/             # Helper functions
└── tests/             # Core-specific tests
```

---

## Key Patterns

### Public ID System

All major entities use `PublicIDModel` to generate unique, shareable identifiers:

```python
class Asset(PublicIDModel):
    name = models.CharField(max_length=255)
    # Automatically gets public_id field
```

### Audit Logging

Critical actions are automatically logged via `AuditLog`:

```python
# Automatically captures: actor, action, target, timestamp, changes
```

### Role-Based Permissions

Users can switch between roles, with permissions evaluated against the active role:

```python
class IsAdminOrReadOnly(BasePermission):
    # Admin has full access, others get read-only
```

---

## Dependencies

- **Django** — Web framework
- **djangorestframework** — API layer
- **djangorestframework-simplejwt** — JWT handling
- **redis** — Caching & message broker
- **channels** — WebSocket support
- **django-redis** — Redis integration

---

## Usage

Other apps import from core:

```python
from core.models import PublicIDModel, AuditLog
from core.permissions import IsAdmin
from core.authentication import JWTAuthentication
from core.pagination import StandardPagination
```

---

## Testing

Core components are tested in `core/tests/`. Run tests specific to core:

```bash
python manage.py test core
```

---

## Related Documentation

- [Authentication](../users/README.md)
- [Asset Model](../assets/models/README.md)
- [API Overview](../README.md)