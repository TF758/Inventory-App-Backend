from django.test import TestCase
from reporting.services.inventory_reports import build_inventory_summary_report

from users.factories.user_factories import (
    UserFactory,
    UserPlacementFactory,
)

from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)


class InventorySummaryBuilderTests(TestCase):
    """
    High-value builder tests.

    Focus:
    - scope filtering
    - zero data safety
    - hierarchy containment
    - cross-scope consistency
    - stable payload contract

    Assumes builder signature:

        build_inventory_summary_payload(
            scope="department|location|room|global",
            scope_id="PUBLIC_ID|None"
        )
    """

    @classmethod
    def setUpTestData(cls):
        # =====================================================
        # Hierarchy A
        # =====================================================
        cls.dept_a = DepartmentFactory(name="Dept A")

        cls.loc_a1 = LocationFactory(
            name="Loc A1",
            department=cls.dept_a,
        )

        cls.loc_a2 = LocationFactory(
            name="Loc A2",
            department=cls.dept_a,
        )

        cls.room_a1 = RoomFactory(
            name="Room A1",
            location=cls.loc_a1,
        )

        cls.room_a2 = RoomFactory(
            name="Room A2",
            location=cls.loc_a1,
        )

        cls.room_a3 = RoomFactory(
            name="Room A3",
            location=cls.loc_a2,
        )

        # =====================================================
        # Hierarchy B
        # =====================================================
        cls.dept_b = DepartmentFactory(name="Dept B")

        cls.loc_b1 = LocationFactory(
            name="Loc B1",
            department=cls.dept_b,
        )

        cls.room_b1 = RoomFactory(
            name="Room B1",
            location=cls.loc_b1,
        )

        # =====================================================
        # Users / placements
        # =====================================================
        cls.user_1 = UserFactory(is_active=True)
        cls.user_2 = UserFactory(is_active=True)
        cls.user_3 = UserFactory(is_active=False)

        UserPlacementFactory(
            user=cls.user_1,
            room=cls.room_a1,
            is_current=True,
        )

        UserPlacementFactory(
            user=cls.user_2,
            room=cls.room_a2,
            is_current=True,
        )

        UserPlacementFactory(
            user=cls.user_3,
            room=cls.room_b1,
            is_current=True,
        )

    # =====================================================
    # Helpers
    # =====================================================

    def build(self, scope, scope_id=None):
        return build_inventory_summary_report(
            scope=scope,
            scope_id=scope_id,
        )

    # =====================================================
    # Contract
    # =====================================================

    def test_builder_returns_expected_root_keys(self):
        payload = self.build("global")

        self.assertIn("meta", payload)
        self.assertIn("data", payload)

    def test_builder_contains_overview_section(self):
        payload = self.build("global")

        self.assertIn(
            "overview",
            payload["data"],
        )

    # =====================================================
    # Zero Data Safety
    # =====================================================

    def test_empty_room_scope_returns_zeroes(self):
        empty_room = RoomFactory()

        payload = self.build(
            "room",
            empty_room.public_id,
        )

        overview = payload["data"]["overview"]

        self.assertEqual(
            overview["total_users"],
            0,
        )

    # =====================================================
    # Scope Filtering
    # =====================================================

    def test_room_scope_only_counts_users_in_that_room(self):
        payload = self.build(
            "room",
            self.room_a1.public_id,
        )

        overview = payload["data"]["overview"]

        self.assertEqual(
            overview["total_users"],
            1,
        )

    def test_location_scope_only_counts_child_rooms(self):
        payload = self.build(
            "location",
            self.loc_a1.public_id,
        )

        overview = payload["data"]["overview"]

        # room_a1 + room_a2 users only
        self.assertEqual(
            overview["total_users"],
            2,
        )

    def test_department_scope_excludes_other_department_users(self):
        payload = self.build(
            "department",
            self.dept_a.public_id,
        )

        overview = payload["data"]["overview"]

        # only dept A users
        self.assertEqual(
            overview["total_users"],
            2,
        )

    def test_global_scope_includes_all_users(self):
        payload = self.build("global")

        overview = payload["data"]["overview"]

        self.assertEqual(
            overview["total_users"],
            3,
        )

    # =====================================================
    # Active Users
    # =====================================================

    def test_active_users_only_counts_active_accounts(self):
        payload = self.build("global")

        users = payload["data"]["users"]

        self.assertEqual(
            users["active"],
            2,
        )

        self.assertEqual(
            users["inactive"],
            1,
        )

    # =====================================================
    # Breakdown Behavior
    # =====================================================

    def test_department_scope_has_location_breakdown(self):
        payload = self.build(
            "department",
            self.dept_a.public_id,
        )

        breakdown = payload["data"]["breakdown"]

        self.assertEqual(
            len(breakdown),
            2,
        )

    def test_location_scope_has_room_breakdown(self):
        payload = self.build(
            "location",
            self.loc_a1.public_id,
        )

        breakdown = payload["data"]["breakdown"]

        self.assertEqual(
            len(breakdown),
            2,
        )

    def test_room_scope_has_no_breakdown(self):
        payload = self.build(
            "room",
            self.room_a1.public_id,
        )

        breakdown = payload["data"].get(
            "breakdown",
            [],
        )

        self.assertEqual(
            len(breakdown),
            0,
        )

    # =====================================================
    # Scope Summary
    # =====================================================

    def test_department_scope_summary_counts_children(self):
        payload = self.build(
            "department",
            self.dept_a.public_id,
        )

        summary = payload["data"]["scope_summary"]

        self.assertEqual(
            summary["departments"],
            1,
        )

        self.assertEqual(
            summary["locations"],
            2,
        )

    def test_location_scope_summary_has_one_location(self):
        payload = self.build(
            "location",
            self.loc_a1.public_id,
        )

        summary = payload["data"]["scope_summary"]

        self.assertEqual(
            summary["locations"],
            1,
        )

    def test_room_scope_summary_has_one_room(self):
        payload = self.build(
            "room",
            self.room_a1.public_id,
        )

        summary = payload["data"]["scope_summary"]

        self.assertEqual(
            summary["rooms"],
            1,
        )