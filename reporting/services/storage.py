from pathlib import PurePosixPath

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import storages


REPORT_STORAGE_ALIAS = "reports"


def get_report_storage():
    return storages[REPORT_STORAGE_ALIAS]


def normalize_report_name(name: str) -> str:
    if not name:
        raise SuspiciousFileOperation("Report storage name is empty.")

    normalized = PurePosixPath(str(name).replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise SuspiciousFileOperation(
            "Report storage name must be a relative key."
        )

    return normalized.as_posix()


def report_exists(name: str) -> bool:
    if not name:
        return False
    return get_report_storage().exists(normalize_report_name(name))


def open_report(name: str, mode: str = "rb"):
    return get_report_storage().open(normalize_report_name(name), mode)


def save_report(name: str, content: bytes) -> str:
    storage = get_report_storage()
    normalized_name = normalize_report_name(name)

    # A report key is deterministic for a ReportJob. Removing an existing
    # object makes retries idempotent for both local and S3-compatible storage.
    if storage.exists(normalized_name):
        storage.delete(normalized_name)

    return storage.save(normalized_name, ContentFile(content))


def delete_report(name: str) -> bool:
    if not name:
        return False

    storage = get_report_storage()
    normalized_name = normalize_report_name(name)
    if not storage.exists(normalized_name):
        return False

    storage.delete(normalized_name)
    return True


def report_download_name(name: str) -> str:
    return PurePosixPath(normalize_report_name(name)).name
