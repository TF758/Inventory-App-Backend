from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from reporting.api.serializers.inventory_report import enforce_inventory_summary_scope
from users.factories.user_factories import (
    UserFactory,
    RoleAssignmentFactory,
)

from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)


class InventorySummaryScopeHelperTests(TestCase):
    """
    Optimized fast tests for inventory scope helper.

    Improvements:
    - Shared users / roles via setUpTestData
    - No per-test factory churn
    - assigned_by reuses same actor user
    """

    @classmethod
    def setUpTestData(cls):
        # =================================================
        # Hierarchy
        # =================================================
        cls.dept_a = DepartmentFactory(name="Dept A")
        cls.loc_a1 = LocationFactory(
            name="Loc A1",
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

        cls.dept_b = DepartmentFactory(name="Dept B")
        cls.loc_b1 = LocationFactory(
            name="Loc B1",
            department=cls.dept_b,
        )
        cls.room_b1 = RoomFactory(
            name="Room B1",
            location=cls.loc_b1,
        )

        # =================================================
        # Users
        # =================================================
        cls.site_user = UserFactory()
        cls.dept_user = UserFactory()
        cls.loc_user = UserFactory()
        cls.room_user = UserFactory()
        cls.no_role_user = UserFactory()

        # =================================================
        # Roles
        # =================================================
        cls.site_role = RoleAssignmentFactory(
            user=cls.site_user,
            assigned_by=cls.site_user,
            site_admin=True,
        )

        cls.dept_role = RoleAssignmentFactory(
            user=cls.dept_user,
            assigned_by=cls.dept_user,
            role="DEPARTMENT_ADMIN",
            department=cls.dept_a,
        )

        cls.loc_role = RoleAssignmentFactory(
            user=cls.loc_user,
            assigned_by=cls.loc_user,
            role="LOCATION_ADMIN",
            location=cls.loc_a1,
        )

        cls.room_role = RoleAssignmentFactory(
            user=cls.room_user,
            assigned_by=cls.room_user,
            role="ROOM_ADMIN",
            room=cls.room_a1,
        )

        # activate roles once
        cls.site_user.active_role = cls.site_role
        cls.site_user.save(update_fields=["active_role"])

        cls.dept_user.active_role = cls.dept_role
        cls.dept_user.save(update_fields=["active_role"])

        cls.loc_user.active_role = cls.loc_role
        cls.loc_user.save(update_fields=["active_role"])

        cls.room_user.active_role = cls.room_role
        cls.room_user.save(update_fields=["active_role"])

    # =====================================================
    # Helpers
    # =====================================================

    def assertDenied(self, user, payload):
        with self.assertRaises(PermissionDenied):
            enforce_inventory_summary_scope(user, payload)

    def assertAllowed(self, user, payload):
        enforce_inventory_summary_scope(user, payload)

    # =====================================================
    # Edge Cases
    # =====================================================

    def test_user_without_active_role_is_denied(self):
        self.assertDenied(
            self.no_role_user,
            {
                "scope": "global",
                "scope_id": None,
            },
        )

    def test_invalid_role_edge_case_is_denied(self):
        role = self.site_role
        role.role = "RANDOM_ROLE"

        self.site_user.active_role = role

        self.assertDenied(
            self.site_user,
            {
                "scope": "global",
                "scope_id": None,
            },
        )

    # =====================================================
    # SITE ADMIN
    # =====================================================

    def test_site_admin_can_access_global(self):
        self.assertAllowed(
            self.site_user,
            {
                "scope": "global",
                "scope_id": None,
            },
        )

    def test_site_admin_can_access_any_department(self):
        self.assertAllowed(
            self.site_user,
            {
                "scope": "department",
                "scope_id": self.dept_b.public_id,
            },
        )

    def test_site_admin_can_access_any_room(self):
        self.assertAllowed(
            self.site_user,
            {
                "scope": "room",
                "scope_id": self.room_b1.public_id,
            },
        )

    # =====================================================
    # DEPARTMENT ADMIN
    # =====================================================

    def test_department_admin_can_access_own_department(self):
        self.assertAllowed(
            self.dept_user,
            {
                "scope": "department",
                "scope_id": self.dept_a.public_id,
            },
        )

    def test_department_admin_can_access_child_location(self):
        self.assertAllowed(
            self.dept_user,
            {
                "scope": "location",
                "scope_id": self.loc_a1.public_id,
            },
        )

    def test_department_admin_can_access_child_room(self):
        self.assertAllowed(
            self.dept_user,
            {
                "scope": "room",
                "scope_id": self.room_a1.public_id,
            },
        )

    def test_department_admin_cannot_access_global(self):
        self.assertDenied(
            self.dept_user,
            {
                "scope": "global",
                "scope_id": None,
            },
        )

    def test_department_admin_cannot_access_other_department(self):
        self.assertDenied(
            self.dept_user,
            {
                "scope": "department",
                "scope_id": self.dept_b.public_id,
            },
        )

    def test_department_admin_cannot_access_other_room(self):
        self.assertDenied(
            self.dept_user,
            {
                "scope": "room",
                "scope_id": self.room_b1.public_id,
            },
        )

    # =====================================================
    # LOCATION ADMIN
    # =====================================================

    def test_location_admin_can_access_own_location(self):
        self.assertAllowed(
            self.loc_user,
            {
                "scope": "location",
                "scope_id": self.loc_a1.public_id,
            },
        )

    def test_location_admin_can_access_child_room(self):
        self.assertAllowed(
            self.loc_user,
            {
                "scope": "room",
                "scope_id": self.room_a2.public_id,
            },
        )

    def test_location_admin_cannot_access_department(self):
        self.assertDenied(
            self.loc_user,
            {
                "scope": "department",
                "scope_id": self.dept_a.public_id,
            },
        )

    def test_location_admin_cannot_access_other_location(self):
        self.assertDenied(
            self.loc_user,
            {
                "scope": "location",
                "scope_id": self.loc_b1.public_id,
            },
        )

    def test_location_admin_cannot_access_other_room(self):
        self.assertDenied(
            self.loc_user,
            {
                "scope": "room",
                "scope_id": self.room_b1.public_id,
            },
        )

    # =====================================================
    # ROOM ADMIN
    # =====================================================

    def test_room_admin_can_access_own_room(self):
        self.assertAllowed(
            self.room_user,
            {
                "scope": "room",
                "scope_id": self.room_a1.public_id,
            },
        )

    def test_room_admin_cannot_access_sibling_room(self):
        self.assertDenied(
            self.room_user,
            {
                "scope": "room",
                "scope_id": self.room_a2.public_id,
            },
        )

    def test_room_admin_cannot_access_location(self):
        self.assertDenied(
            self.room_user,
            {
                "scope": "location",
                "scope_id": self.loc_a1.public_id,
            },
        )

    def test_room_admin_cannot_access_department(self):
        self.assertDenied(
            self.room_user,
            {
                "scope": "department",
                "scope_id": self.dept_a.public_id,
            },
        )

    def test_room_admin_cannot_access_global(self):
        self.assertDenied(
            self.room_user,
            {
                "scope": "global",
                "scope_id": None,
            },
        )

    # =====================================================
    # Case Insensitive IDs
    # =====================================================

    def test_scope_id_matching_is_case_insensitive(self):
        self.assertAllowed(
            self.dept_user,
            {
                "scope": "department",
                "scope_id": self.dept_a.public_id.lower(),
            },
        )