# Data Import — Bulk Asset Import

> Django app for bulk importing assets from CSV files.

The `data_import` app provides a scalable pipeline for importing large batches of equipment, accessories, and consumables via CSV uploads.

---

## Overview

The data_import app enables organizations to migrate existing inventory data or perform bulk updates via CSV files. Imports are processed asynchronously via Celery, with results tracked via the reporting system.

This follows the **async job** pattern — large file processing is offloaded to background workers.

---

## What Data Import Provides

### Import Workflow

1. User uploads CSV file via API
2. File is stored and a `ReportJob` is created
3. Celery task processes the file asynchronously
4. Results are stored in the job's `result_payload`
5. User is notified upon completion

### Supported Asset Types

| Type       | Importer             | Description                          |
| ---------- | -------------------- | ------------------------------------ |
| Equipment  | `EquipmentImporter`  | Import equipment with serial numbers |
| Accessory  | `AccessoryImporter`  | Import accessories                   |
| Consumable | `ConsumableImporter` | Import consumables with quantities   |

### Import Builder

Central function that routes to the correct importer:

```python
def build_asset_import(
    *,
    asset_type: str,
    stored_file_name: str,
    generated_by=None,
    job=None,
) -> dict:
    importer = get_asset_importer(
        asset_type,
        user=generated_by,
        job=job,
    )

    return importer.run(stored_file_name=stored_file_name)
```

### Asset Importers

Each asset type has a dedicated importer:

- **EquipmentImporter** — Handles equipment CSV format
- **AccessoryImporter** — Handles accessory CSV format
- **ConsumableImporter** — Handles consumable CSV format

All importers extend a base class with common validation and error handling.

---

## Architecture

```
data_import/
├── models.py           # (minimal, uses reporting models)
├── views.py            # API views for upload/status
├── serializers.py      # Request validation
├── tasks.py            # Celery tasks
├── services/           # Import logic
│   ├── import_builder.py    # Main entry point
│   ├── base_importer.py     # Base importer class
│   ├── equipment_importer.py
│   ├── accessory_importer.py
│   └── consumable_importer.py
├── factory.py          # Importer factory
├── renderers.py        # Excel output for import results
├── utils.py            # File storage utilities
├── tests/              # Unit tests
└── import_urls.py      # URL routing
```

---

## Key Patterns

### CSV Upload

```python
class AssetImportCreateView(APIView):
    def post(self, request):
        serializer = AssetImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        asset_type = serializer.validated_data["asset_type"]

        # Store file
        stored_file_name = store_import_upload(uploaded_file)

        # Create job
        job = ReportJob.objects.create(
            user=request.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": asset_type,
                "stored_file_name": stored_file_name,
                "original_file_name": uploaded_file.name,
            },
        )

        # Queue async task
        run_asset_import_task.delay(job.id)

        return Response({"job_id": job.public_id}, status=202)
```

### Async Task

```python
@shared_task
def run_asset_import_task(job_id):
    job = ReportJob.objects.get(id=job_id)
    job.status = ReportJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save()

    try:
        result = build_asset_import(
            asset_type=job.params["asset_type"],
            stored_file_name=job.params["stored_file_name"],
            generated_by=job.user,
            job=job,
        )

        job.result_payload = result
        job.status = ReportJob.Status.DONE
    except Exception as e:
        job.error = str(e)
        job.status = ReportJob.Status.FAILED
    finally:
        job.finished_at = timezone.now()
        job.save()
```

### Importer Factory

```python
def get_asset_importer(asset_type, user=None, job=None):
    importers = {
        "equipment": EquipmentImporter,
        "accessory": AccessoryImporter,
        "consumable": ConsumableImporter,
    }

    importer_class = importers.get(asset_type)
    if not importer_class:
        raise ValueError(f"Unknown asset type: {asset_type}")

    return importer_class(user=user, job=job)
```

---

## Usage

### Uploading a CSV

```python
import requests

# Upload equipment CSV
with open("equipment.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/import/assets/",
        files={"file": f},
        data={"asset_type": "equipment"},
        headers={"Authorization": "Bearer <token>"}
    )

# Response
{
    "job_id": "RPT-XXXXX",
    "status": "pending",
    "message": "Import started."
}
```

### Checking Import Status

```python
# Poll for status
response = requests.get(
    "http://localhost:8000/api/import/assets/RPT-XXXXX/status/",
    headers={"Authorization": "Bearer <token>"}
)

# When complete
{
    "job_id": "RPT-XXXXX",
    "status": "done",
    "result": {
        "total_rows": 100,
        "success_count": 95,
        "error_count": 5,
        "errors": [...]
    }
}
```

### CSV Format Example (Equipment)

```csv
name,brand,model,serial_number,status,room_public_id
Dell Laptop,Dell,XPS 15,SN123456,ok,RM-XXXXX
HP Monitor,HP,24 inch,HP987654,ok,RM-XXXXX
```

---

## Dependencies

- **reporting** — ReportJob model for tracking
- **assets** — Equipment, Accessory, Consumable models
- **core** — Audit and notification mixins
- **Celery** — Async task processing

---

## API Endpoints

| Method | Endpoint                                | Description           |
| ------ | --------------------------------------- | --------------------- |
| POST   | `/api/import/assets/`                   | Upload CSV for import |
| GET    | `/api/import/assets/{job_id}/status/`   | Check import status   |
| GET    | `/api/import/assets/{job_id}/download/` | Download error report |

---

## Testing

Run data_import-specific tests:

```bash
python manage.py test data_import
```

---

## Related Documentation

- [Assets](../assets/README.md)
- [Reporting](../reporting/README.md)
- [Core Models](../core/README.md)
- [API Overview](../README.md)
