# Reporting — Async Report Generation

> Django app handling asynchronous report generation, job management, and Excel export.

The `reporting` app provides a scalable reporting pipeline that generates reports asynchronously via Celery, delivering results as Excel files.

---

## Overview

The reporting app implements an async job system for generating various reports. Users request reports via API, and Celery workers process them in the background, notifying users upon completion.

This follows the **job queue** pattern — long-running report generation is offloaded to background workers.

---

## What Reporting Provides

### ReportJob Model

Tracks async report generation jobs:

```python
class ReportJob(PublicIDModel):
    PUBLIC_ID_PREFIX = "RPT"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class ReportType(models.TextChoices):
        USER_SUMMARY = "user_summary", "User Summary"
        SITE_ASSETS = "site_assets", "Site Assets"
        SITE_AUDIT_LOGS = "site_audit_logs", "Site Audit Logs"
        ASSET_IMPORT = "asset_import", "Asset Import"
        USER_AUDIT_HISTORY = "user_audit_history", "User Audit History"
        USER_LOGIN_HISTORY = "user_login_history", "User Login History"
        ASSET_HISTORY = "asset_history", "Asset History"
        INVENTORY_SUMMARY = "inventory_summary", "Inventory Summary"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="report_jobs")
    report_type = models.CharField(max_length=40, choices=ReportType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    params = models.JSONField()
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    report_file = models.CharField(max_length=500, blank=True)

    result_payload = models.JSONField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)
```

### Report Types

| Type                 | Description                         |
| -------------------- | ----------------------------------- |
| `USER_SUMMARY`       | Summary of user activity and assets |
| `SITE_ASSETS`        | Assets at a specific site           |
| `SITE_AUDIT_LOGS`    | Audit logs for a site               |
| `ASSET_IMPORT`       | Bulk asset import results           |
| `USER_AUDIT_HISTORY` | User's audit trail                  |
| `USER_LOGIN_HISTORY` | User login history                  |
| `ASSET_HISTORY`      | Asset lifecycle history             |
| `INVENTORY_SUMMARY`  | Overall inventory summary           |

### Report Registry

The `report_registry.py` module defines all available reports:

```python
# Each report defines:
- builder: Function that gathers report data
- renderer: Function that converts data to Excel workbook
- param_map: Translates stored params to builder arguments
```

Workflow:

1. API request creates `ReportJob` with `report_type` and `params`
2. Celery task `generate_report_task` is triggered
3. Registry lookup finds the report definition
4. `param_map` converts stored params to builder args
5. `builder` collects the data
6. `renderer` builds Excel workbook spec
7. Excel file is written to disk
8. User is notified

---

## Architecture

```
reporting/
├── models/
│   └── reports.py      # ReportJob model
├── api/
│   ├── serializers/    # DRF serializers
│   └── viewsets/       # API view sets
├── selectors/          # QuerySet builders
├── services/           # Report builder functions
│   ├── inventory_reports.py
│   ├── asset_reports.py
│   ├── site_reports.py
│   └── user_summary.py
├── tasks/              # Celery tasks
├── filters/            # Filter backends
├── tests/              # Unit tests
├── urls/               # URL routing
├── utils/
│   └── report_adapters/  # Excel renderer functions
└── report_registry.py  # Report definitions
```

---

## Key Patterns

### Job Status Tracking

```python
job = ReportJob.objects.create(
    user=user,
    report_type=ReportJob.ReportType.INVENTORY_SUMMARY,
    params={"filters": {}},
    status=ReportJob.Status.PENDING
)

# Check status
if job.status == ReportJob.Status.DONE:
    # Report ready
    file_path = job.report_file
elif job.status == ReportJob.Status.FAILED:
    # Handle error
    error_msg = job.error
```

### Report Builder Functions

Each report type has a builder function:

```python
def build_inventory_summary_report(filters, generated_by):
    # Collect inventory data
    return {
        "summary": {...},
        "assets": [...],
    }
```

### Excel Renderers

Convert builder output to Excel:

```python
def inventory_summary_to_workbook_spec(data):
    # Return workbook specification
    return {
        "sheets": [
            {"name": "Summary", "data": [...]},
            {"name": "Assets", "data": [...]},
        ]
    }
```

---

## Usage

### Requesting a Report

```python
from reporting.models import ReportJob

job = ReportJob.objects.create(
    user=request.user,
    report_type=ReportJob.ReportType.INVENTORY_SUMMARY,
    params={"filters": {"status": "ok"}}
)

# Celery task is triggered automatically
```

### Checking Job Status

```python
job = ReportJob.objects.get(public_id="RPT-XXXXX")

print(f"Status: {job.get_status_display()}")
print(f"Created: {job.created_at}")
print(f"Finished: {job.finished_at}")

if job.status == ReportJob.Status.DONE:
    print(f"File: {job.report_file}")
elif job.status == ReportJob.Status.FAILED:
    print(f"Error: {job.error}")
```

### Querying User Reports

```python
# Get all reports for current user
user.report_jobs.all()

# Get pending/running reports
user.report_jobs.filter(
    status__in=[ReportJob.Status.PENDING, ReportJob.Status.RUNNING]
)
```

---

## Dependencies

- **core** — PublicIDModel, base classes
- **users** — User model
- **assets** — Asset data for reports
- **sites** — Site data for reports
- **Celery** — Async task processing
- **openpyxl** — Excel file generation

---

## API Endpoints

Typical endpoints:

- `GET /api/reports/` — List user's report jobs
- `POST /api/reports/` — Create new report job
- `GET /api/reports/{public_id}/` — Get report job status
- `DELETE /api/reports/{public_id}/` — Cancel report job
- `GET /api/reports/{public_id}/download/` — Download completed report

---

## Testing

Run reporting-specific tests:

```bash
python manage.py test reporting
```

---

## Related Documentation

- [Assets](../assets/README.md)
- [Sites](../sites/README.md)
- [Users](../users/README.md)
- [Core Models](../core/README.md)
- [API Overview](../README.md)
