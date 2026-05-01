# Reporting Tests — Coverage Overview

> Quick reference for developers to understand what's tested in the reporting module.

---

## Test Files Summary

| Test File                               | What Is Covered                                                               |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| `test_user_summary_report.py`           | User demographics, login stats, audit summary report builder                  |
| `test_user_login_history_report.py`     | User login history within date range, event counting                          |
| `test_user_audit_history_report.py`     | User audit events aggregation, history rows                                   |
| `test_site_audit_log_report.py`         | Site-level audit log filtering by department/location/room                    |
| `test_site_asset_report.py`             | Site asset counts by type (equipment, consumable), multi-type support         |
| `test_inventory_summary_permissions.py` | Scope enforcement (global, department, location, room)                        |
| `test_inventory_summary_builder.py`     | Inventory summary builder with scope filtering, zero-data handling            |
| `test_download_report.py`               | Report download API: pending (202), failed (409), missing file (404), success |

---

## Coverage by Area

### Report Builders (Services)

- ✅ **User Summary Report** — Demographics, login stats, audit summary sections
- ✅ **User Login History** — Date range filtering, login event counting
- ✅ **User Audit History** — Event aggregation, history rows
- ✅ **Site Audit Log** — Site scope filtering, audit period
- ✅ **Site Asset Report** — Asset counts by type, multi-type handling
- ✅ **Inventory Summary** — Scope filtering, hierarchy containment, zero-data safety

### Permissions / Scope Enforcement

- ✅ **Inventory Summary Scope** — Global, department, location, room-level access control
- ✅ **User-specific reports** — User existence validation

### API Endpoints

- ✅ **Download Report** — Status handling (pending, failed, done), file serving

### Edge Cases

- ✅ **Missing user** — Builder raises ValueError
- ✅ **Empty data** — Builder returns empty structures gracefully
- ✅ **Multiple asset types** — Report includes all requested types

---

## Potential Future Coverage

- **Performance tests** — Large dataset handling, query optimization
- **Export formats** — Excel file content validation beyond structure
- **Scheduled reports** — Celery task integration tests
- **Concurrent report generation** — Race condition handling
- **Invalid date ranges** — Start/end date validation
- **Cross-scope access** — Users accessing reports outside their scope

---

## Running Tests

```bash
# Run all reporting tests
python manage.py test reporting

# Run specific test file
python manage.py test reporting.tests.reports.test_user_summary_report

# Run with coverage
coverage run --manage.py test reporting
coverage report --include="reporting/*"
```

---

## Related Documentation

- [Reporting](../reporting/README.md) — Report types and architecture
- [Core Tests](../core/README.md) — Core module test coverage
