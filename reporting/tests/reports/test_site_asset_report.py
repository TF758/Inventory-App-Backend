from django.test import TestCase
from django.utils import timezone

from db_inventory.factories.user_factories import UserFactory
from db_inventory.factories.site_factories import ( DepartmentFactory, LocationFactory, RoomFactory, )
from db_inventory.factories.asset_factories import ( EquipmentFactory, ComponentFactory, ConsumableFactory, AccessoryFactory, )
from reporting.services.site_reports import build_site_asset_report
from reporting.utils.report_adapters.site_reports import site_asset_to_workbook_spec


class SiteAssetReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory()

        cls.department = DepartmentFactory(name="IT")
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

    # -------------------------------------------------
    # Builder Tests
    # -------------------------------------------------

    def test_builder_returns_structure(self):

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertIn("assets", result)
        self.assertIn("totals", result)


    def test_builder_counts_equipment(self):

        EquipmentFactory.create_batch(
            2,
            room=self.room,
        )

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertEqual(result["totals"]["equipment"], 2)


    def test_builder_handles_multiple_asset_types(self):

        EquipmentFactory(room=self.room)
        ConsumableFactory(room=self.room)

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment", "consumable"],
        )

        self.assertIn("equipment", result["assets"])
        self.assertIn("consumable", result["assets"])


    def test_builder_returns_empty_when_no_assets(self):

        result = build_site_asset_report(
            site_type="department",
            site_id=self.department.public_id,
            asset_types=["equipment"],
        )

        self.assertEqual(result["totals"]["equipment"], 0)
        self.assertEqual(result["assets"]["equipment"], [])


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

        self.assertEqual(result["totals"]["equipment"], 1)


    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_report_info_sheet(self):

        payload = {
            "meta": {
                "generated_at": timezone.now(),
                "generated_by": "tester",
                "site_type": "department",
                "site_id": "DEP123",
                "site_name": "IT",
            },
            "data": {
                "assets": {
                    "equipment": []
                }
            },
        }

        spec = site_asset_to_workbook_spec(payload)

        self.assertIn("Report Info", spec)


    def test_renderer_creates_asset_sheet(self):

        payload = {
            "meta": {},
            "data": {
                "assets": {
                    "equipment": [
                        {
                            "name": "Laptop",
                            "brand": "Dell",
                            "model": "XPS",
                            "serial_number": "123",
                            "public_id": "EQP1",
                        }
                    ]
                }
            },
        }

        spec = site_asset_to_workbook_spec(payload)

        self.assertIn("Equipment", spec)
        self.assertEqual(spec["Equipment"]["headers"][0], "name")


    def test_renderer_handles_empty_asset_lists(self):

        payload = {
            "meta": {},
            "data": {
                "assets": {
                    "equipment": []
                }
            },
        }

        spec = site_asset_to_workbook_spec(payload)

        self.assertEqual(
            spec["Equipment"]["rows"][0][0],
            "No equipment records found for this site.",
        )