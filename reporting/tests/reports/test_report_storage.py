from django.core.exceptions import SuspiciousFileOperation
from django.test import SimpleTestCase

from reporting.services.storage import (
    delete_report,
    get_report_storage,
    normalize_report_name,
    open_report,
    report_download_name,
    report_exists,
    save_report,
)


class ReportStorageTests(SimpleTestCase):
    def tearDown(self):
        delete_report("report-storage-test.xlsx")

    def test_save_open_and_delete_report_through_named_storage(self):
        stored_name = save_report(
            "report-storage-test.xlsx",
            b"first payload",
        )

        self.assertEqual(stored_name, "report-storage-test.xlsx")
        self.assertTrue(report_exists(stored_name))

        with open_report(stored_name) as report_file:
            self.assertEqual(report_file.read(), b"first payload")

        self.assertTrue(delete_report(stored_name))
        self.assertFalse(report_exists(stored_name))

    def test_save_overwrites_deterministic_report_key(self):
        save_report("report-storage-test.xlsx", b"first payload")
        save_report("report-storage-test.xlsx", b"replacement payload")

        with open_report("report-storage-test.xlsx") as report_file:
            self.assertEqual(
                report_file.read(),
                b"replacement payload",
            )

    def test_storage_alias_is_available(self):
        self.assertIsNotNone(get_report_storage())

    def test_download_name_does_not_expose_storage_prefix(self):
        self.assertEqual(
            report_download_name("private/reports/result.xlsx"),
            "result.xlsx",
        )

    def test_parent_path_segments_are_rejected(self):
        with self.assertRaises(SuspiciousFileOperation):
            normalize_report_name("../secret.txt")
