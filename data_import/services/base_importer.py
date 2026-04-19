import csv
from dataclasses import dataclass, field

from django.core.files.storage import default_storage

from sites.models.sites import Room
from core.permissions.helpers import has_hierarchy_permission, is_in_scope, is_viewer_role
import pandas as pd
import io

from data_import.utils import load_and_normalize_csv

@dataclass
class ImportRowIssue:
    row_number: int
    status: str
    reason: str
    row_data: dict = field(default_factory=dict)


@dataclass
class ImportResult:
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0
    issues: list[ImportRowIssue] = field(default_factory=list)

    def add_imported(self):
        self.imported_rows += 1

    def add_skipped(self, row_number: int, reason: str, row_data: dict):
        self.skipped_rows += 1
        self.issues.append(
            ImportRowIssue(
                row_number=row_number,
                status="skipped",
                reason=reason,
                row_data=row_data,
            )
        )

    def add_failed(self, row_number: int, reason: str, row_data: dict):
        self.failed_rows += 1
        self.issues.append(
            ImportRowIssue(
                row_number=row_number,
                status="failed",
                reason=reason,
                row_data=row_data,
            )
        )


class BaseAssetImporter:
    required_headers = set()
    allowed_headers = set()
    serializer_class = None

    def __init__(self, *, user):
        self.user = user
        self.seen_keys = set()

    def run(self, *, stored_file_name: str) -> dict:
        result = ImportResult()

        if not stored_file_name:
            raise ValueError("Import file path is missing.")

        if not default_storage.exists(stored_file_name):
            raise ValueError(f"Import file not found: {stored_file_name}")

        # -----------------------------
        # Load and normalize CSV
        # -----------------------------
        with default_storage.open(stored_file_name, "rb") as f:
            df = load_and_normalize_csv(f)
        
        # print("Detected columns:", df.columns.tolist())

        headers = set(df.columns)

        missing = self.required_headers - headers
        extra = headers - self.allowed_headers

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )

        if extra:
            raise ValueError(
                f"Unexpected columns: {', '.join(sorted(extra))}"
            )

        rows = df.to_dict(orient="records")

        result.total_rows = len(rows)

        if result.total_rows > 10_000:
            raise ValueError("CSV exceeds the 10,000 row limit.")

        # -----------------------------
        # Process rows
        # -----------------------------
        for index, raw_row in enumerate(rows, start=2):

            try:
                row_data = self.normalize_row(raw_row)

                room = self.resolve_room(row_data)
                self.check_write_permission(room)

                dedupe_key = self.get_file_dedupe_key(row_data, room)

                # duplicate in file
                if dedupe_key in self.seen_keys:
                    result.add_skipped(
                        index,
                        "Duplicate row in file.",
                        raw_row,
                    )
                    continue

                self.seen_keys.add(dedupe_key)

                # duplicate in database
                if self.exists_in_db(row_data, room):
                    result.add_skipped(
                        index,
                        "Duplicate asset already exists.",
                        raw_row,
                    )
                    continue

                payload = self.build_payload(row_data, room)

                serializer = self.serializer_class(data=payload)

                if not serializer.is_valid():
                    result.add_failed(
                        index,
                        str(serializer.errors),
                        raw_row,
                    )
                    continue

                serializer.save()
                result.add_imported()

            except PermissionError as exc:
                result.add_skipped(index, str(exc), raw_row)

            except ValueError as exc:
                result.add_failed(index, str(exc), raw_row)

            except Exception as exc:
                result.add_failed(
                    index,
                    f"Unexpected error: {exc}",
                    raw_row,
                )

        return self.to_payload(result)

    def to_payload(self, result: ImportResult) -> dict:
        return {
            "summary": {
                "total_rows": result.total_rows,
                "imported_rows": result.imported_rows,
                "skipped_rows": result.skipped_rows,
                "failed_rows": result.failed_rows,
            },
            "issues": [
                {
                    "row_number": item.row_number,
                    "status": item.status,
                    "reason": item.reason,
                    "row_data": item.row_data,
                }
                for item in result.issues
            ],
        }

    def _is_blank_row(self, row: dict) -> bool:
        return all(not str(v or "").strip() for v in row.values())

    def normalize_row(self, row: dict) -> dict:
        return {
            key: value.strip() if isinstance(value, str) else value
            for key, value in row.items()
        }

    def resolve_room(self, row: dict):
        room_public_id = (row.get("room") or "").strip()

        if not room_public_id:
            raise ValueError("Room is required.")

        room = Room.objects.filter(public_id=room_public_id).first()

        if not room:
            raise ValueError(f"Room '{room_public_id}' does not exist.")

        return room

    def check_write_permission(self, room):
        active_role = getattr(self.user, "active_role", None)

        if not active_role:
            raise PermissionError("User has no active role.")

        if active_role.role == "SITE_ADMIN":
            return

        if is_viewer_role(active_role.role):
            raise PermissionError("User does not have permission to import assets.")

        if not has_hierarchy_permission(active_role.role, "ROOM_CLERK"):
            raise PermissionError(
                "User does not have sufficient role to import assets."
            )

        if not is_in_scope(active_role, room=room):
            raise PermissionError(
                f"User is out of scope for room '{room.public_id}'."
            )

    def build_payload(self, row: dict, room):
        raise NotImplementedError

    def get_file_dedupe_key(self, row: dict, room):
        raise NotImplementedError

    def exists_in_db(self, row: dict, room):
        raise NotImplementedError