from types import SimpleNamespace

from django.test import SimpleTestCase

from access.hierachy import (
    DEPARTMENT,
    LOCATION,
    ROOM,
    SITE,
)
from access.services.hierachy import HierarchyService



class HierarchyServiceTests(SimpleTestCase):
    """
    Unit tests for HierarchyService.

    HierarchyService answers:

        - Which site hierarchy levels can this active role navigate?
        - At which hierarchy level can this target role type be assigned?

    These tests intentionally do not test:
        - permissions / capabilities
        - object scope
        - role governance
        - serializers
        - DRF permissions
    """

    def make_role_assignment(self, role):
        return SimpleNamespace(role=role)

    # ------------------------------------------------------------------
    # Missing / unknown role config
    # ------------------------------------------------------------------

    def test_missing_role_assignment_has_no_access(self):
        self.assertFalse(
            HierarchyService.can_access_site(None)
        )
        self.assertFalse(
            HierarchyService.can_access_department(None)
        )
        self.assertFalse(
            HierarchyService.can_access_location(None)
        )
        self.assertFalse(
            HierarchyService.can_access_room(None)
        )

    def test_unknown_role_has_no_access(self):
        role_assignment = self.make_role_assignment("UNKNOWN_ROLE")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_room(role_assignment)
        )

    def test_unknown_role_cannot_be_assigned_anywhere(self):
        self.assertFalse(
            HierarchyService.can_assign_to_site("UNKNOWN_ROLE")
        )
        self.assertFalse(
            HierarchyService.can_assign_to_department("UNKNOWN_ROLE")
        )
        self.assertFalse(
            HierarchyService.can_assign_to_location("UNKNOWN_ROLE")
        )
        self.assertFalse(
            HierarchyService.can_assign_to_room("UNKNOWN_ROLE")
        )

    # ------------------------------------------------------------------
    # SITE_ADMIN navigation
    # ------------------------------------------------------------------

    def test_site_admin_can_access_department_location_and_room(self):
        role_assignment = self.make_role_assignment("SITE_ADMIN")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    # ------------------------------------------------------------------
    # Department role navigation
    # ------------------------------------------------------------------

    def test_department_admin_can_access_department_location_and_room(self):
        role_assignment = self.make_role_assignment("DEPARTMENT_ADMIN")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    def test_department_viewer_can_access_department_location_and_room(self):
        role_assignment = self.make_role_assignment("DEPARTMENT_VIEWER")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    # ------------------------------------------------------------------
    # Location role navigation
    # ------------------------------------------------------------------

    def test_location_admin_can_access_location_and_room_only(self):
        role_assignment = self.make_role_assignment("LOCATION_ADMIN")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    def test_location_viewer_can_access_location_and_room_only(self):
        role_assignment = self.make_role_assignment("LOCATION_VIEWER")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    # ------------------------------------------------------------------
    # Room role navigation
    # ------------------------------------------------------------------

    def test_room_admin_can_access_room_only(self):
        role_assignment = self.make_role_assignment("ROOM_ADMIN")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    def test_room_clerk_can_access_room_only(self):
        role_assignment = self.make_role_assignment("ROOM_CLERK")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    def test_room_viewer_can_access_room_only(self):
        role_assignment = self.make_role_assignment("ROOM_VIEWER")

        self.assertFalse(
            HierarchyService.can_access_site(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_department(role_assignment)
        )
        self.assertFalse(
            HierarchyService.can_access_location(role_assignment)
        )
        self.assertTrue(
            HierarchyService.can_access_room(role_assignment)
        )

    # ------------------------------------------------------------------
    # Assignment placement
    # ------------------------------------------------------------------

    def test_site_admin_role_can_only_be_assigned_to_site(self):
        self.assertTrue(
            HierarchyService.can_assign_to_site("SITE_ADMIN")
        )
        self.assertFalse(
            HierarchyService.can_assign_to_department("SITE_ADMIN")
        )
        self.assertFalse(
            HierarchyService.can_assign_to_location("SITE_ADMIN")
        )
        self.assertFalse(
            HierarchyService.can_assign_to_room("SITE_ADMIN")
        )

    def test_department_roles_can_only_be_assigned_to_department(self):
        for role in [
            "DEPARTMENT_ADMIN",
            "DEPARTMENT_VIEWER",
        ]:
            with self.subTest(role=role):
                self.assertFalse(
                    HierarchyService.can_assign_to_site(role)
                )
                self.assertTrue(
                    HierarchyService.can_assign_to_department(role)
                )
                self.assertFalse(
                    HierarchyService.can_assign_to_location(role)
                )
                self.assertFalse(
                    HierarchyService.can_assign_to_room(role)
                )

    def test_location_roles_can_only_be_assigned_to_location(self):
        for role in [
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
        ]:
            with self.subTest(role=role):
                self.assertFalse(
                    HierarchyService.can_assign_to_site(role)
                )
                self.assertFalse(
                    HierarchyService.can_assign_to_department(role)
                )
                self.assertTrue(
                    HierarchyService.can_assign_to_location(role)
                )
                self.assertFalse(
                    HierarchyService.can_assign_to_room(role)
                )

    def test_room_roles_can_only_be_assigned_to_room(self):
        for role in [
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        ]:
            with self.subTest(role=role):
                self.assertFalse(
                    HierarchyService.can_assign_to_site(role)
                )
                self.assertFalse(
                    HierarchyService.can_assign_to_department(role)
                )
                self.assertFalse(
                    HierarchyService.can_assign_to_location(role)
                )
                self.assertTrue(
                    HierarchyService.can_assign_to_room(role)
                )

    # ------------------------------------------------------------------
    # Generic assignment method
    # ------------------------------------------------------------------

    def test_can_assign_uses_target_role_not_actor_role(self):
        """
        Regression test for the old bug class:

        The assignment level must be checked against the target role type,
        not the actor's active role.
        """

        self.assertTrue(
            HierarchyService.can_assign(
                "ROOM_ADMIN",
                ROOM,
            )
        )
        self.assertFalse(
            HierarchyService.can_assign(
                "ROOM_ADMIN",
                DEPARTMENT,
            )
        )

        self.assertTrue(
            HierarchyService.can_assign(
                "DEPARTMENT_ADMIN",
                DEPARTMENT,
            )
        )
        self.assertFalse(
            HierarchyService.can_assign(
                "DEPARTMENT_ADMIN",
                ROOM,
            )
        )

    def test_can_assign_returns_false_for_unknown_level(self):
        self.assertFalse(
            HierarchyService.can_assign(
                "ROOM_ADMIN",
                "unknown",
            )
        )

    def test_can_assign_matches_specific_helpers(self):
        role_level_pairs = [
            ("SITE_ADMIN", SITE),
            ("DEPARTMENT_ADMIN", DEPARTMENT),
            ("DEPARTMENT_VIEWER", DEPARTMENT),
            ("LOCATION_ADMIN", LOCATION),
            ("LOCATION_VIEWER", LOCATION),
            ("ROOM_ADMIN", ROOM),
            ("ROOM_CLERK", ROOM),
            ("ROOM_VIEWER", ROOM),
        ]

        for role, level in role_level_pairs:
            with self.subTest(role=role, level=level):
                self.assertEqual(
                    HierarchyService.can_assign(role, level),
                    {
                        SITE: HierarchyService.can_assign_to_site,
                        DEPARTMENT: HierarchyService.can_assign_to_department,
                        LOCATION: HierarchyService.can_assign_to_location,
                        ROOM: HierarchyService.can_assign_to_room,
                    }[level](role),
                )