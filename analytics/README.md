# Analytics — Metrics & Snapshots

> Django app for tracking system-wide metrics, daily snapshots, and historical data for dashboards and reporting.

The `analytics` app provides the data layer for operational dashboards, tracking inventory counts, user activity, authentication events, and department-level snapshots over time.

---

## Overview

The analytics app captures and stores historical metrics about the system — from daily inventory counts to user login activity. These metrics power dashboards, enable trend analysis, and support strategic decision-making.

This follows the **time-series snapshot** pattern — capturing point-in-time state for historical comparison.

---

## What Analytics Provides

### DailySystemMetrics

System-wide daily metrics:

```python
class DailySystemMetrics(models.Model):
    date = models.DateField(unique=True)

    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    human_users = models.PositiveIntegerField(default=0)
    system_users = models.PositiveIntegerField(default=0)
    active_users_last_24h = models.PositiveIntegerField(default=0)
    active_users_last_7d = models.PositiveIntegerField(default=0)
    new_users_last_24h = models.PositiveIntegerField(default=0)
    locked_users = models.PositiveIntegerField(default=0)

    # Session metrics
    total_sessions = models.PositiveIntegerField(default=0)
    active_sessions = models.PositiveIntegerField(default=0)
    revoked_sessions = models.PositiveIntegerField(default=0)
    expired_sessions_last_24h = models.PositiveIntegerField(default=0)
    unique_users_logged_in_last_24h = models.PositiveIntegerField(default=0)

    # Inventory metrics
    total_equipment = models.PositiveIntegerField(default=0)
    equipment_ok = models.PositiveIntegerField(default=0)
    equipment_under_repair = models.PositiveIntegerField(default=0)
    equipment_damaged = models.PositiveIntegerField(default=0)

    total_components = models.PositiveIntegerField(default=0)
    total_components_quantity = models.PositiveIntegerField(default=0)
    total_consumables = models.PositiveIntegerField(default=0)
    total_consumables_quantity = models.PositiveIntegerField(default=0)
    total_accessories = models.PositiveIntegerField(default=0)
    total_accessories_quantity = models.PositiveIntegerField(default=0)
```

Metrics captured:

- **User counts** — total, human, system, active, new, locked
- **Session counts** — total, active, revoked, expired
- **Inventory counts** — equipment, components, consumables, accessories with quantities
- **Equipment status breakdown** — OK, under repair, damaged

### DailyAuthMetrics

Daily authentication and security metrics:

```python
class DailyAuthMetrics(models.Model):
    date = models.DateField(unique=True, db_index=True)

    # Login events
    total_logins = models.PositiveIntegerField(default=0)
    unique_users_logged_in = models.PositiveIntegerField(default=0)
    failed_logins = models.PositiveIntegerField(default=0)
    lockouts = models.PositiveIntegerField(default=0)

    # Sessions
    active_sessions = models.PositiveIntegerField(default=0)
    revoked_sessions = models.PositiveIntegerField(default=0)
    expired_sessions = models.PositiveIntegerField(default=0)
    users_multiple_active_sessions = models.PositiveIntegerField(default=0)
    users_with_revoked_sessions = models.PositiveIntegerField(default=0)

    # Password resets
    password_resets_started = models.PositiveIntegerField(default=0)
    password_resets_completed = models.PositiveIntegerField(default=0)
    active_password_resets = models.PositiveIntegerField(default=0)
    expired_password_resets = models.PositiveIntegerField(default=0)
```

Metrics captured:

- **Login activity** — total logins, unique users, failed attempts, lockouts
- **Session management** — active, revoked, expired counts
- **Password resets** — started, completed, active, expired

### DailyDepartmentSnapshot

Per-department daily snapshots:

```python
class DailyDepartmentSnapshot(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="daily_snapshots")
    snapshot_date = models.DateField(default=timezone.localdate, db_index=True)

    total_users = models.PositiveIntegerField(default=0)
    total_admins = models.PositiveIntegerField(default=0)

    total_locations = models.PositiveIntegerField(default=0)
    total_rooms = models.PositiveIntegerField(default=0)

    total_equipment = models.PositiveIntegerField(default=0)
    equipment_ok = models.PositiveIntegerField(default=0)
    equipment_under_repair = models.PositiveIntegerField(default=0)
    equipment_damaged = models.PositiveIntegerField(default=0)

    total_components = models.PositiveIntegerField(default=0)
    total_components_quantity = models.PositiveIntegerField(default=0)

    total_consumables = models.PositiveIntegerField(default=0)
    total_consumables_quantity = models.PositiveIntegerField(default=0)

    total_accessories = models.PositiveIntegerField(default=0)
    total_accessories_quantity = models.PositiveIntegerField(default=0)

    total_return_requests = models.PositiveIntegerField(default=0)
    pending_return_requests = models.PositiveIntegerField(default=0)
    approved_return_requests = models.PositiveIntegerField(default=0)
    denied_return_requests = models.PositiveIntegerField(default=0)
    partial_return_requests = models.PositiveIntegerField(default=0)

    returns_created_last_24h = models.PositiveIntegerField(default=0)
    returns_processed_last_24h = models.PositiveIntegerField(default=0)
```

Snapshots capture:

- **User counts** — total users, admin count
- **Location counts** — locations and rooms
- **Inventory** — equipment, components, consumables, accessories with quantities
- **Equipment status** — OK, under repair, damaged
- **Return requests** — total, pending, approved, denied, partial
- **Activity** — returns created/processed in last 24h

---

## Architecture

```
analytics/
├── models/
│   ├── metrics.py     # DailySystemMetrics, DailyAuthMetrics
│   └── snapshots.py   # DailyDepartmentSnapshot
├── api/
│   ├── serializers/   # DRF serializers
│   └── viewsets/      # API view sets
├── selectors/         # QuerySet builders
├── services/          # Metric calculation services
├── tasks/             # Celery tasks for daily collection
├── management/
│   └── commands/      # Django management commands
├── filters/           # Filter backends
├── factories/         # Test factories
├── tests/             # Unit tests
├── urls/              # URL routing
└── utils/             # Helper functions
```

---

## Key Patterns

### Daily Collection

Metrics are collected daily via Celery tasks:

```python
# Celery task runs daily
@shared_task
def collect_daily_metrics():
    # Collect system metrics
    DailySystemMetrics.objects.create(...)

    # Collect auth metrics
    DailyAuthMetrics.objects.create(...)

    # Collect department snapshots
    for department in Department.objects.all():
        DailyDepartmentSnapshot.objects.create(...)
```

### Querying Historical Data

```python
# Get last 30 days of system metrics
metrics = DailySystemMetrics.objects.order_by('-date')[:30]

# Get department snapshot for specific date
snapshot = DailyDepartmentSnapshot.objects.filter(
    department=dept,
    snapshot_date=date
).first()
```

### Dashboard Integration

```python
# Get latest metrics for dashboard
latest = DailySystemMetrics.objects.first()

# Equipment health percentage
if latest.total_equipment > 0:
    health_pct = (latest.equipment_ok / latest.total_equipment) * 100
```

---

## Usage

### Accessing System Metrics

```python
from analytics.models import DailySystemMetrics

# Get today's metrics
today = DailySystemMetrics.objects.filter(date=date.today()).first()

# Get last 7 days
week_metrics = DailySystemMetrics.objects.order_by('-date')[:7]

# Calculate trends
for metric in week_metrics:
    print(f"{metric.date}: {metric.total_equipment} equipment, {metric.active_users_last_24h} active users")
```

### Accessing Auth Metrics

```python
from analytics.models import DailyAuthMetrics

auth_today = DailyAuthMetrics.objects.filter(date=date.today()).first()

print(f"Logins: {auth_today.total_logins}")
print(f"Failed: {auth_today.failed_logins}")
print(f"Lockouts: {auth_today.lockouts}")
```

### Accessing Department Snapshots

```python
from analytics.models import DailyDepartmentSnapshot

# Get department snapshot
snapshot = DailyDepartmentSnapshot.objects.filter(
    department=department,
    snapshot_date=date.today()
).first()

print(f"Equipment: {snapshot.total_equipment}")
print(f"OK: {snapshot.equipment_ok}")
print(f"Damaged: {snapshot.equipment_damaged}")
print(f"Pending Returns: {snapshot.pending_return_requests}")
```

---

## Dependencies

- **core** — Base classes
- **users** — User and session data
- **assets** — Asset inventory data
- **sites** — Department, Location, Room data
- **assignments** — Return request data
- **Celery** — Scheduled task execution

---

## API Endpoints

Typical endpoints:

- `GET /api/analytics/system/` — Get system metrics
- `GET /api/analytics/system/history/` — Get historical system metrics
- `GET /api/analytics/auth/` — Get auth metrics
- `GET /api/analytics/departments/{id}/` — Get department snapshot
- `GET /api/analytics/departments/{id}/history/` — Get department history

---

## Testing

Run analytics-specific tests:

```bash
python manage.py test analytics
```

---

## Related Documentation

### Domain Modules

- [Assets](../assets/README.md)
- [Sites](../sites/README.md)
- [Users](../users/README.md)
- [Assignments](../assignments/README.md)
- [Reporting](../reporting/README.md)
