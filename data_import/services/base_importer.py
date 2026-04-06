import csv
import io
from dataclasses import dataclass, field
from typing import Any

from django.core.files.base import ContentFile
from django.utils import timezone

from inventory.data_import.models import ImportJob
from inventory.db_inventory.models.site import Room
from inventory.db_inventory.permissions.helpers import is_in_scope




@dataclass
class RowResult:
    row_number: int
    status: str  # imported / skipped / failed
    reason: str
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportSummary:
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0
    rows: list[RowResult] = field(default_factory=list)

    def add_imported(self, row_number: int, raw_data: dict[str, Any]) -> None:
        self.imported_rows += 1
        self.rows.append(RowResult(row_number=row_number, status="imported", reason="", raw_data=raw_data))

    def add_skipped(self, row_number: int, reason: str, raw_data: dict[str, Any]) -> None:
        self.skipped_rows += 1
        self.rows.append(RowResult(row_number=row_number, status="skipped", reason=reason, raw_data=raw_data))

    def add_failed(self, row_number: int, reason: str, raw_data: dict[str, Any]) -> None:
        self.failed_rows += 1
        self.rows.append(RowResult(row_number=row_number, status="failed", reason=reason, raw_data=raw_data))


class BaseAssetImporter:
    required_headers: set[str] = set()
    allowed_headers: set[str] = set()
    serializer_class = None
    asset_type: str = ""

    def __init__(self, *, job: ImportJob):
        self.job = job
        self.user = job.created_by
        self.summary = ImportSummary()
        self._seen_keys: set[tuple] = set()

    def run(self) -> ImportSummary:
        self.job.status = ImportJob.Status.RUNNING
        self.job.started_at = timezone.now()
        self.job.save(update_fields=["status", "started_at"])

        try:
            rows = self._read_csv()
            self.summary.total_rows = len(rows)
            self._validate_row_limit(rows)

            for row_number, raw_row in enumerate(rows, start=2):  # header is row 1
                if self._is_blank_row(raw_row):
                    continue

                try:
                    normalized = self.normalize_row(raw_row)
                    room = self.resolve_room(normalized)
                    self.check_room_permission(room)

                    dedupe_key = self.get_dedupe_key(normalized, room)
                    if dedupe_key in self._seen_keys:
                        self.summary.add_skipped(row_number, "Duplicate row in file.", normalized)
                        continue
                    self._seen_keys.add(dedupe_key)

                    if self.is_duplicate(normalized, room):
                        self.summary.add_skipped(row_number, "Duplicate asset already exists.", normalized)
                        continue

                    payload = self.build_serializer_payload(normalized, room)
                    serializer = self.serializer_class(data=payload, context={"request": None})

                    if not serializer.is_valid():
                        self.summary.add_failed(row_number, self.format_serializer_errors(serializer.errors), normalized)
                        continue

                    serializer.save()
                    self.summary.add_imported(row_number, normalized)

                except PermissionError as exc:
                    self.summary.add_skipped(row_number, str(exc), raw_row)
                except ValueError as exc:
                    self.summary.add_failed(row_number, str(exc), raw_row)
                except Exception as exc:
                    self.summary.add_failed(row_number, f"Unexpected error: {exc}", raw_row)

            self._attach_report()
            self._finalize_success()
            return self.summary

        except Exception as exc:
            self.job.status = ImportJob.Status.FAILED
            self.job.error_message = str(exc)
            self.job.finished_at = timezone.now()
            self.job.save(update_fields=["status", "error_message", "finished_at"])
            raise

    def _read_csv(self) -> list[dict[str, str]]:
        self.job.source_file.open("rb")
        raw_bytes = self.job.source_file.read()
        text = raw_bytes.decode("utf-8-sig")
        stream = io.StringIO(text)
        reader = csv.DictReader(stream)

        if not reader.fieldnames:
            raise ValueError("CSV file is missing a header row.")

        headers = {h.strip() for h in reader.fieldnames if h}
        missing = self.required_headers - headers
        extra = headers - self.allowed_headers

        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
        if extra:
            raise ValueError(f"Unexpected columns: {', '.join(sorted(extra))}")

        return list(reader)

    def _validate_row_limit(self, rows: list[dict[str, str]]) -> None:
        if len(rows) > 10_000:
            raise ValueError("CSV exceeds the maximum allowed row limit of 10,000.")

    def _is_blank_row(self, row: dict[str, Any]) -> bool:
        return all(not str(value or "").strip() for value in row.values())

    def resolve_room(self, row: dict[str, Any]) -> Room:
        room_public_id = (row.get("room") or "").strip()
        if not room_public_id:
            raise ValueError("Room is required.")

        room = Room.objects.filter(public_id=room_public_id).first()
        if not room:
            raise ValueError(f"Room '{room_public_id}' does not exist.")
        return room

    def check_room_permission(self, room: Room) -> None:
        active_role = getattr(self.user, "active_role", None)
        if not active_role:
            raise PermissionError("User has no active role.")
        if active_role.role == "SITE_ADMIN":
            return
        if not is_in_scope(active_role, room=room):
            raise PermissionError(f"No permission for room '{room.public_id}'.")

    def _attach_report(self) -> None:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["row", "status", "reason", "data"])

        for item in self.summary.rows:
            if item.status == "imported":
                continue
            writer.writerow([
                item.row_number,
                item.status,
                item.reason,
                item.raw_data,
            ])

        report_name = f"import_job_{self.job.id}_report.csv"
        self.job.report_file.save(report_name, ContentFile(output.getvalue().encode("utf-8")))
        output.close()

    def _finalize_success(self) -> None:
        self.job.status = ImportJob.Status.COMPLETED
        self.job.total_rows = self.summary.total_rows
        self.job.imported_rows = self.summary.imported_rows
        self.job.skipped_rows = self.summary.skipped_rows
        self.job.failed_rows = self.summary.failed_rows
        self.job.finished_at = timezone.now()
        self.job.save(
            update_fields=[
                "status",
                "total_rows",
                "imported_rows",
                "skipped_rows",
                "failed_rows",
                "finished_at",
                "report_file",
            ]
        )

    def format_serializer_errors(self, errors: dict[str, Any]) -> str:
        return str(errors)

    def normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    def build_serializer_payload(self, row: dict[str, Any], room: Room) -> dict[str, Any]:
        raise NotImplementedError

    def get_dedupe_key(self, row: dict[str, Any], room: Room) -> tuple:
        raise NotImplementedError

    def is_duplicate(self, row: dict[str, Any], room: Room) -> bool:
        raise NotImplementedError