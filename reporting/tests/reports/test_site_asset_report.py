from django.test import TestCase
from django.utils import timezone

from assets.asset_factories import ConsumableFactory, EquipmentFactory
from users.factories.user_factories import UserFactory
from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)
from reporting.services.site_reports import build_site_asset_report
from reporting.utils.report_adapters.site_reports import (
    site_asset_to_workbook_spec,
)


class SiteAssetReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.department = DepartmentFactory(name="IT")
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

    def _meta(self):
        return {
            "report_name": "Site Asset Report",
            "generated_at": timezone.now(),
            "generated_by": "tester",
            "site_type": "department",
            "site_id": "DEP123",
            "site_name": "IT",
        }

    # -------------------------------------------------
    # Builder Tests
    # -------------------------------------------------

    def test_builder_returns_structure(self):
        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertIn("meta", result)
        self.assertIn("data", result)
        self.assertIn("summary", result["data"])
        self.assertIn("tables", result["data"])

    def test_builder_counts_equipment(self):
        EquipmentFactory.create_batch(2, room=self.room)

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertEqual(
            result["data"]["summary"]["equipment_count"],
            2,
        )

    def test_builder_handles_multiple_asset_types(self):
        EquipmentFactory(room=self.room)
        ConsumableFactory(room=self.room)

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment", "consumable"],
        )

        self.assertIn("Equipment", result["data"]["tables"])
        self.assertIn("Consumable", result["data"]["tables"])

    def test_builder_returns_empty_when_no_assets(self):
        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertEqual(
            result["data"]["summary"]["equipment_count"],
            0,
        )

        self.assertEqual(
            result["data"]["tables"]["Equipment"],
            [],
        )

    def test_builder_respects_site_scope(self):
        other_dept = DepartmentFactory()

        other_loc = LocationFactory(department=other_dept)
        other_room = RoomFactory(location=other_loc)

        EquipmentFactory(room=self.room)
        EquipmentFactory(room=other_room)

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertEqual(
            result["data"]["summary"]["equipment_count"],
            1,
        )

    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_report_info_sheet(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "equipment_count": 0,
                    "grand_total": 0,
                },
                "tables": {
                    "Equipment": [],
                },
            },
        }

        spec = site_asset_to_workbook_spec(payload)

        self.assertIn("Report Info", spec)

    def test_renderer_creates_asset_sheet(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "equipment_count": 1,
                    "grand_total": 1,
                },
                "tables": {
                    "Equipment": [
                        {
                            "name": "Laptop",
                            "brand": "Dell",
                            "model": "XPS",
                            "serial_number": "123",
                            "public_id": "EQP1",
                        }
                    ],
                },
            },
        }

        spec = site_asset_to_workbook_spec(payload)

        self.assertIn("Equipment", spec)

    def test_renderer_handles_empty_asset_lists(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "equipment_count": 0,
                    "grand_total": 0,
                },
                "tables": {
                    "Equipment": [],
                },
            },
        }

        spec = site_asset_to_workbook_spec(payload)

        self.assertIn("Equipment", spec)