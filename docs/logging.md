# Logging

The Inventory System implements a comprehensive multi-layer logging architecture combining operational system logging with immutable audit trails for security and compliance.

## Overview

The logging system operates on two distinct levels:

1. **Application Logging**: Operational and debug logs for system monitoring and troubleshooting
2. **Audit Logging**: Immutable records of user actions and system events for compliance and security

## Application Logging (System Level)

### Configuration

Application logging is configured via `settings.py` and environment variables, allowing runtime tuning without code changes.

#### Environment Variables

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# App log rotation (midnight rotation, keep 30 days)
LOG_FILE_WHEN=midnight
LOG_FILE_INTERVAL=1
LOG_FILE_BACKUP_COUNT=30

# Error log rotation (separate error log file)
LOG_ERROR_WHEN=midnight
LOG_ERROR_INTERVAL=1
LOG_ERROR_BACKUP_COUNT=30

# Console output (optional, useful in development)
LOG_TO_CONSOLE=True

# Log archival and deletion
LOG_ARCHIVE_AFTER_DAYS=7
LOG_DELETE_AFTER_DAYS=7

# Cron schedule for log archival (runs at 2:15 AM daily)
LOG_ARCHIVE_CRON=15 2 * * *

# Log directory location
LOGS_DIR=logs/
```

### Log Handlers

Two separate log handlers are configured:

#### App Handler

- **File**: `logs/app.log`
- **Level**: Configured via `LOG_LEVEL` (default: INFO)
- **Rotation**: Daily by default
- **Retention**: 30 backup files (30 days with daily rotation)
- **Format**: Detailed with request ID tracking

#### Error Handler

- **File**: `logs/error.log`
- **Level**: ERROR
- **Rotation**: Daily by default
- **Retention**: 30 backup files
- **Format**: Same as app handler for consistency

#### Console Handler (Optional)

- **Target**: stderr
- **Level**: Configured via `LOG_LEVEL`
- **Enabled by**: `LOG_TO_CONSOLE` environment variable
- **Useful for**: Docker containers, local development

### Log Format

All logs use a detailed format with structured context:

```
%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s | request_id=%(request_id)s
```

Example output:

```
2026-05-06 14:23:45,123 | INFO | arms.data_import | import_service.py:45 (process_batch) | Batch import started | request_id=DBG-a1b2c3d4e5
```

### Request ID Tracking

The `RequestIDFilter` automatically injects a request ID into every log record:

- Format: `DBG-{10 hex digits}`
- Set via `RequestIDMiddleware` at request entry
- Included in every log record for distributed tracing
- Useful for correlating logs across services

### Logger Instantiation

Applications should use the provided helper function:

```python
from core.logging import get_logger

# Get a logger scoped to the application
logger = get_logger("data_import")  # Creates "arms.data_import" logger

# Log with optional extra context
logger.info("import_started", extra={
    "job_id": job.public_id,
    "record_count": 1500
})
```

All extra fields are automatically captured and included in the structured log output.

## Log Archival and Maintenance

### Automatic Log Archival

The `archive_logs` Celery task manages log file lifecycle:

1. **Detection**: Identifies rotated log files by date pattern
2. **Archival**: Compresses logs older than `LOG_ARCHIVE_AFTER_DAYS` to `logs/archive/`
3. **Deletion**: Removes archived logs after `LOG_DELETE_AFTER_DAYS`

#### Scheduling

Runs on a configurable cron schedule (default: 2:15 AM daily):

```python
LOG_ARCHIVE_CRON = "15 2 * * *"  # Daily at 2:15 AM
```

#### ScheduledTaskRun Tracking

The `archive_logs` task creates a `ScheduledTaskRun` record for monitoring:

```python
class ScheduledTaskRun(models.Model):
    task_name = models.CharField(max_length=100)  # "archive_logs"
    run_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("started", "Started"),
            ("success", "Success"),
            ("skipped", "Skipped"),
            ("failed", "Failed"),
        ]
    )
    message = models.TextField()  # Status details
    duration_ms = models.PositiveIntegerField()  # Execution time
```

### Manual Setup Command

Initialize or update logging infrastructure:

```bash
python manage.py setup_logger
```

This command:

- Creates log directory if missing
- Initializes log rotation configuration
- Schedules Celery Beat tasks for archival
- Verifies logger configuration

### Retention Policy Configuration

```python
# settings.py
TASKRUN_SUCCESS_RETENTION_DAYS = 7      # Successful task runs
TASKRUN_SKIPPED_RETENTION_DAYS = 14     # Skipped task runs
TASKRUN_FAILED_RETENTION_DAYS = 90      # Failed task runs

LOG_ARCHIVE_AFTER_DAYS = 7              # Archive log files after 7 days
LOG_DELETE_AFTER_DAYS = 7               # Delete archived logs after 7 days
```

## Audit Logging (Application Level)

### Overview

The `AuditLog` model provides immutable, tamper-proof audit trails for all significant user and system actions.

### AuditLog Model

Located in `core/models/audit.py`:

```python
class AuditLog(PublicIDModel):
    # Actor
    user = ForeignKey(User, on_delete=models.SET_NULL, null=True)
    user_public_id = CharField()  # Snapshot (if user deleted)
    user_email = EmailField()     # Snapshot

    # Event
    event_type = CharField(max_length=100)  # "login", "equipment_created", etc.
    description = CharField(max_length=255)
    metadata = JSONField()  # Custom structured data

    # Target
    target_model = CharField()  # "Equipment", "User", etc.
    target_id = CharField()    # Public ID
    target_name = CharField()  # Snapshot label

    # Scope (hierarchical context)
    department = ForeignKey(Department, null=True)
    department_name = CharField()
    location = ForeignKey(Location, null=True)
    location_name = CharField()
    room = ForeignKey(Room, null=True)
    room_name = CharField()

    # Request context
    ip_address = GenericIPAddressField()
    user_agent = CharField()

    # Timestamps
    created_at = DateTimeField(db_index=True)
```

#### Immutability Guarantees

- **No Modification**: `save()` raises `RuntimeError` if `pk` exists
- **No Deletion**: `delete()` raises `RuntimeError`
- **Write-Once**: Records are created once and never changed
- **Database Indexes**: On `event_type`, `created_at`, `user`, `target_model`, `target_id`

### AuditMixin

The `AuditMixin` (in `core/mixins.py`) automatically captures audit logs in viewsets:

#### Usage in Viewsets

```python
from core.mixins import AuditMixin
from rest_framework import viewsets

class EquipmentModelViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
        # Audit log auto-captured on success
```

#### Manual Audit Logging

```python
from core.mixins import AuditMixin

class CustomView(AuditMixin, APIView):
    def post(self, request):
        # Custom business logic
        user = User.objects.get(id=request.data.get("user_id"))

        # Log the event
        self._log_audit(
            event_type="custom_action",
            target=user,
            description="Custom user action performed",
            metadata={
                "action_detail": "something specific",
                "amount": 100,
            }
        )

        return Response({"status": "success"})
```

#### Scope Resolution

The mixin automatically resolves scope hierarchy:

```python
# If target has room → captures room, location, department
# If target has location → captures location, department
# If target has department → captures department
```

This enables filtering and reporting by organizational unit.

#### Event Constants

Common event types are predefined in `AuditLog.Events`:

```python
class Events:
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    ACCOUNT_LOCKED = "account_locked"
    USER_CREATED = "user_created"
    # ... many more
```

### Audit Log Querying

#### Via ORM

```python
from core.models.audit import AuditLog

# Recent logins
logins = AuditLog.objects.filter(
    event_type=AuditLog.Events.LOGIN,
    created_at__gte=timezone.now() - timedelta(days=1)
).order_by('-created_at')

# User activity
user_events = AuditLog.objects.filter(
    user__public_id="USR-123"
).order_by('-created_at')

# Department changes
dept_changes = AuditLog.objects.filter(
    department__id=dept_id,
    event_type__in=[
        AuditLog.Events.USER_CREATED,
        AuditLog.Events.USER_UPDATED,
    ]
)
```

#### Via API

List audit logs with filtering:

```
GET /api/audit-logs/
GET /api/audit-logs/?event_type=login
GET /api/audit-logs/?user__public_id=USR-123
GET /api/audit-logs/?department__id=1
GET /api/audit-logs/?created_at__gte=2026-05-01
```

### Compliance and Security

#### Data Retention

- Audit logs are designed for long-term retention
- Configure retention policy per compliance requirements
- Archive old records separately from deletion
- All records include timestamps for temporal queries

#### Sensitive Data

- User snapshots (`user_email`, `user_public_id`) prevent audit log gaps if users deleted
- Request context (IP, user agent) for security analysis
- Metadata allows custom sensitive fields per event

#### Access Control

- Audit logs are read-only (no modification after creation)
- Typically accessible only to administrators
- Consider separate database backup for legal holds

## Scheduled Tasks (ScheduledTaskRun)

The `ScheduledTaskRun` model (in `core/models/tasks.py`) tracks execution of background tasks:

```python
class ScheduledTaskRun(models.Model):
    task_name = CharField(max_length=100, db_index=True)
    run_at = DateTimeField(auto_now_add=True)
    status = CharField(
        max_length=20,
        choices=[
            ("started", "Started"),
            ("success", "Success"),
            ("skipped", "Skipped"),
            ("failed", "Failed"),
        ]
    )
    message = TextField(blank=True)
    duration_ms = PositiveIntegerField(null=True)
    schema_version = PositiveSmallIntegerField(null=True)
```

### Task Examples

- `archive_logs` - Compress and archive old log files
- `cleanup_notifications` - Soft delete and purge old notifications
- `cleanup_sessions` - Remove expired user sessions
- `daily_metrics` - Calculate system metrics
- Task runs are queryable for monitoring task health

### Monitoring

```python
from core.models.tasks import ScheduledTaskRun

# Recent task executions
recent = ScheduledTaskRun.objects.filter(
    run_at__gte=timezone.now() - timedelta(hours=24)
).order_by('-run_at')

# Failed tasks
failed = ScheduledTaskRun.objects.filter(
    status=ScheduledTaskRun.Status.FAILED
).order_by('-run_at')[:10]

# Performance (average duration)
successes = ScheduledTaskRun.objects.filter(
    task_name="archive_logs",
    status=ScheduledTaskRun.Status.SUCCESS
)
avg_duration = successes.aggregate(models.Avg('duration_ms'))
```

## Logging Best Practices

### Application Code

1. **Use `get_logger()`** for module-level loggers
2. **Include context** in extra fields (IDs, counts, statuses)
3. **Use appropriate levels**: DEBUG for flow, INFO for events, WARNING for issues
4. **Avoid sensitive data** in log messages (passwords, tokens, PII)

```python
from core.logging import get_logger

logger = get_logger("equipment_import")

def import_equipment(file):
    logger.info("import_started", extra={"filename": file.name})
    try:
        equipment = Equipment.objects.create(...)
        logger.info("equipment_created", extra={"equipment_id": equipment.public_id})
    except Exception as e:
        logger.error("import_failed", extra={"error": str(e)})
        raise
```

### ViewSet Usage

1. **Extend AuditMixin** for automatic audit capture
2. **Provide event types** from `AuditLog.Events`
3. **Include metadata** for business context
4. **Use scope objects** for hierarchical tracking

```python
from core.mixins import AuditMixin

class EquipmentViewSet(AuditMixin, viewsets.ModelViewSet):
    # Audit logs auto-captured on create/update/delete
    # Custom actions:
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        equipment = self.get_object()
        user = User.objects.get(id=request.data['user_id'])

        equipment.assigned_to = user
        equipment.save()

        self._log_audit(
            event_type="equipment_assigned",
            target=equipment,
            description=f"Assigned to {user.email}",
            metadata={"assigned_to_user_id": user.public_id}
        )

        return Response({"status": "assigned"})
```

## Troubleshooting

### Logs Not Being Written

1. Check `LOGS_DIR` exists and is writable
2. Verify `LOG_LEVEL` is not set to CRITICAL
3. Check file permissions: `chmod 755 logs/`
4. Ensure Python logging is not disabled globally

### High Disk Usage

1. Lower `LOG_FILE_BACKUP_COUNT` to keep fewer backups
2. Reduce `LOG_ARCHIVE_AFTER_DAYS` for faster archival
3. Verify `archive_logs` task runs successfully
4. Check for very large log entries (malformed requests, stack traces)

### Missing Audit Logs

1. Verify viewset extends `AuditMixin`
2. Check `_log_audit()` is called with correct parameters
3. For tests, ensure `IS_TESTING` setting is handled
4. Check database constraints for AuditLog inserts

### Celery Task Failures

1. Check Celery worker is running: `celery -A inventory worker -l debug`
2. Verify Redis connection: `redis-cli ping`
3. Check `ScheduledTaskRun` records for error messages
4. Review Celery logs for exceptions
