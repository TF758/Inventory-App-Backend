from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import OperationalError
from django.test import TestCase

from data_import.services.base_importer import BaseAssetImporter


class TransientFailureImporter(BaseAssetImporter):
    required_headers = {"value"}
    allowed_headers = required_headers

    def resolve_room(self, row):
        return object()

    def check_write_permission(self, room):
        return None

    def get_file_dedupe_key(self, row, room):
        return row["value"]

    def exists_in_db(self, row, room):
        raise OperationalError("database temporarily unavailable")


class ImporterReliabilityTests(TestCase):
    def test_transient_row_failure_escapes_to_the_celery_retry_boundary(self):
        stored_name = default_storage.save(
            "imports/source/transient.csv",
            ContentFile(b"value\nLaptop\n"),
        )
        self.addCleanup(
            lambda: default_storage.exists(stored_name)
            and default_storage.delete(stored_name)
        )

        importer = TransientFailureImporter(user=object())

        with self.assertRaises(OperationalError):
            importer.run(stored_file_name=stored_name)
