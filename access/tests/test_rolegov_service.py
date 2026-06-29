


from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.hierachy import MANAGES_ALL
from access.services.roles import RoleGovernanceService


class RoleGovernanceServiceTests(SimpleTestCase):
    """
    Unit tests for RoleGovernanceService.

    RoleGovernanceService answers:

        - Which role types an actor may govern.
        - Whether the target assignment scope is valid.
        - Whether role governance + scope validation pass together.

    These tests intentionally do not test:
        - permission/capability checks
        - object queryset visibility
        - serializers
        - DRF permissions
        - database persistence
    """

    def make_actor_role(
        self,
        role,
        *,
        department_id=None,
        location_id=None,
        room_id=None,
    ):
        return SimpleNamespace(
            role=role,
            department_id=department_id,
            location_id=location_id,
            room_id=room_id,
        )

    def make_department(self, id=1):
        return SimpleNamespace(id=id)

    def make_location(self, id=1, department_id=1):
        return SimpleNamespace(
            id=id,
            department_id=department_id,
        )

    def make_room(self, id=1, location_id=1):
        return SimpleNamespace(
            id=id,
            location_id=location_id,
        )

    def make_assignment(
        self,
        role,
        *,
        room=None,
        location=None,
        department=None,
    ):
        return SimpleNamespace(
            role=role,
            room=room,
            location=location,
            department=department,
        )

    # ------------------------------------------------------------------
    # Managed role config
    # ------------------------------------------------------------------

    def test_missing_actor_role_manages_no_roles(self):
        self.assertEqual(
            RoleGovernanceService.get_manageable_roles(None),
            set(),
        )

    def test_site_admin_manages_all_roles(self):
        actor_role = self.make_actor_role("SITE_ADMIN")

        self.assertEqual(
            RoleGovernanceService.get_manageable_roles(actor_role),
            MANAGES_ALL,
        )

    def test_department_admin_manageable_roles(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )

        self.assertEqual(
            RoleGovernanceService.get_manageable_roles(actor_role),
            {
                "LOCATION_ADMIN",
                "LOCATION_VIEWER",
                "ROOM_ADMIN",
                "ROOM_CLERK",
                "ROOM_VIEWER",
            },
        )

    def test_location_admin_manageable_roles(self):
        actor_role = self.make_actor_role(
            "LOCATION_ADMIN",
            location_id=1,
        )

        self.assertEqual(
            RoleGovernanceService.get_manageable_roles(actor_role),
            {
                "ROOM_ADMIN",
                "ROOM_CLERK",
                "ROOM_VIEWER",
            },
        )

    def test_room_admin_manageable_roles(self):
        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )

        self.assertEqual(
            RoleGovernanceService.get_manageable_roles(actor_role),
            {
                "ROOM_CLERK",
                "ROOM_VIEWER",
            },
        )

    def test_viewer_and_clerk_roles_manage_nothing(self):
        for role in [
            "DEPARTMENT_VIEWER",
            "LOCATION_VIEWER",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        ]:
            with self.subTest(role=role):
                actor_role = self.make_actor_role(role)

                self.assertEqual(
                    RoleGovernanceService.get_manageable_roles(actor_role),
                    set(),
                )

    # ------------------------------------------------------------------
    # can_assign_role
    # ------------------------------------------------------------------

    def test_can_assign_role_returns_false_without_actor_role(self):
        self.assertFalse(
            RoleGovernanceService.can_assign_role(
                None,
                "ROOM_VIEWER",
            )
        )

    def test_can_assign_role_returns_false_without_target_role(self):
        actor_role = self.make_actor_role("ROOM_ADMIN")

        self.assertFalse(
            RoleGovernanceService.can_assign_role(
                actor_role,
                None,
            )
        )

    def test_site_admin_can_assign_any_role_type(self):
        actor_role = self.make_actor_role("SITE_ADMIN")

        for target_role in [
            "SITE_ADMIN",
            "DEPARTMENT_ADMIN",
            "DEPARTMENT_VIEWER",
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        ]:
            with self.subTest(target_role=target_role):
                self.assertTrue(
                    RoleGovernanceService.can_assign_role(
                        actor_role,
                        target_role,
                    )
                )

    def test_department_admin_can_assign_managed_roles(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )

        for target_role in [
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        ]:
            with self.subTest(target_role=target_role):
                self.assertTrue(
                    RoleGovernanceService.can_assign_role(
                        actor_role,
                        target_role,
                    )
                )

    def test_department_admin_cannot_assign_unmanaged_roles(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )

        for target_role in [
            "SITE_ADMIN",
            "DEPARTMENT_ADMIN",
            "DEPARTMENT_VIEWER",
        ]:
            with self.subTest(target_role=target_role):
                self.assertFalse(
                    RoleGovernanceService.can_assign_role(
                        actor_role,
                        target_role,
                    )
                )

    def test_location_admin_can_assign_room_roles_only(self):
        actor_role = self.make_actor_role(
            "LOCATION_ADMIN",
            location_id=1,
        )

        self.assertTrue(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "ROOM_ADMIN",
            )
        )
        self.assertTrue(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "ROOM_CLERK",
            )
        )
        self.assertTrue(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "ROOM_VIEWER",
            )
        )

        self.assertFalse(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "LOCATION_VIEWER",
            )
        )
        self.assertFalse(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "DEPARTMENT_ADMIN",
            )
        )

    def test_room_admin_can_assign_room_clerk_and_room_viewer_only(self):
        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )

        self.assertTrue(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "ROOM_CLERK",
            )
        )
        self.assertTrue(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "ROOM_VIEWER",
            )
        )

        self.assertFalse(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "ROOM_ADMIN",
            )
        )
        self.assertFalse(
            RoleGovernanceService.can_assign_role(
                actor_role,
                "LOCATION_ADMIN",
            )
        )

    # ------------------------------------------------------------------
    # Department scope assignment
    # ------------------------------------------------------------------

    def test_site_admin_can_assign_department_role_to_any_department(self):
        actor_role = self.make_actor_role("SITE_ADMIN")
        department = self.make_department(id=99)

        self.assertTrue(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "DEPARTMENT_ADMIN",
                department=department,
            )
        )

    def test_department_actor_can_assign_department_role_to_own_department(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        department = self.make_department(id=1)

        self.assertTrue(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "DEPARTMENT_VIEWER",
                department=department,
            )
        )

    def test_department_actor_cannot_assign_department_role_outside_department(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        department = self.make_department(id=2)

        self.assertFalse(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "DEPARTMENT_VIEWER",
                department=department,
            )
        )

    def test_department_scope_rejects_non_department_target_role(self):
        actor_role = self.make_actor_role(
            "SITE_ADMIN",
        )
        department = self.make_department(id=1)

        self.assertFalse(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "ROOM_ADMIN",
                department=department,
            )
        )

    # ------------------------------------------------------------------
    # Location scope assignment
    # ------------------------------------------------------------------

    def test_site_admin_can_assign_location_role_to_any_location(self):
        actor_role = self.make_actor_role("SITE_ADMIN")
        location = self.make_location(
            id=99,
            department_id=99,
        )

        self.assertTrue(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "LOCATION_ADMIN",
                location=location,
            )
        )

    def test_department_actor_can_assign_location_role_inside_department(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        location = self.make_location(
            id=10,
            department_id=1,
        )

        self.assertTrue(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "LOCATION_ADMIN",
                location=location,
            )
        )

    def test_department_actor_cannot_assign_location_role_outside_department(self):
        actor_role = self.make_actor_role(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        location = self.make_location(
            id=10,
            department_id=2,
        )

        self.assertFalse(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "LOCATION_ADMIN",
                location=location,
            )
        )

    def test_location_actor_can_assign_location_role_to_own_location(self):
        actor_role = self.make_actor_role(
            "LOCATION_ADMIN",
            location_id=10,
        )
        location = self.make_location(
            id=10,
            department_id=1,
        )

        self.assertTrue(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "LOCATION_VIEWER",
                location=location,
            )
        )

    def test_location_actor_cannot_assign_location_role_to_other_location(self):
        actor_role = self.make_actor_role(
            "LOCATION_ADMIN",
            location_id=10,
        )
        location = self.make_location(
            id=11,
            department_id=1,
        )

        self.assertFalse(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "LOCATION_VIEWER",
                location=location,
            )
        )

    def test_location_scope_rejects_non_location_target_role(self):
        actor_role = self.make_actor_role("SITE_ADMIN")
        location = self.make_location(id=1, department_id=1)

        self.assertFalse(
            RoleGovernanceService.can_assign_scope(
                actor_role,
                "ROOM_ADMIN",
                location=location,
            )
        )

    # ------------------------------------------------------------------
    # Room scope assignment
    # ------------------------------------------------------------------

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_room_scope_delegates_to_scope_service_for_room_roles(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = True

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(id=1)

        result = RoleGovernanceService.can_assign_scope(
            actor_role,
            "ROOM_VIEWER",
            room=room,
        )

        self.assertTrue(result)
        mock_can_access_room.assert_called_once_with(
            actor_role,
            room,
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_room_scope_returns_false_when_scope_service_denies_room(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = False

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(id=2)

        result = RoleGovernanceService.can_assign_scope(
            actor_role,
            "ROOM_VIEWER",
            room=room,
        )

        self.assertFalse(result)
        mock_can_access_room.assert_called_once_with(
            actor_role,
            room,
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_room_scope_rejects_non_room_target_role_before_scope_check(
        self,
        mock_can_access_room,
    ):
        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(id=1)

        result = RoleGovernanceService.can_assign_scope(
            actor_role,
            "LOCATION_ADMIN",
            room=room,
        )

        self.assertFalse(result)
        mock_can_access_room.assert_not_called()

    # ------------------------------------------------------------------
    # Combined can_assign
    # ------------------------------------------------------------------

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_assign_returns_true_when_role_and_scope_are_allowed(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = True

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(id=1)

        self.assertTrue(
            RoleGovernanceService.can_assign(
                actor_role,
                "ROOM_VIEWER",
                room=room,
            )
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_assign_returns_false_when_role_is_not_managed(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = True

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(id=1)

        self.assertFalse(
            RoleGovernanceService.can_assign(
                actor_role,
                "ROOM_ADMIN",
                room=room,
            )
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_assign_returns_false_when_scope_is_denied(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = False

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(id=2)

        self.assertFalse(
            RoleGovernanceService.can_assign(
                actor_role,
                "ROOM_VIEWER",
                room=room,
            )
        )

    def test_can_assign_returns_false_without_scope(self):
        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )

        self.assertFalse(
            RoleGovernanceService.can_assign(
                actor_role,
                "ROOM_VIEWER",
            )
        )

    # ------------------------------------------------------------------
    # can_manage_assignment
    # ------------------------------------------------------------------

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_manage_assignment_returns_true_for_managed_assignment_inside_scope(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = True

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        assignment = self.make_assignment(
            "ROOM_VIEWER",
            room=self.make_room(id=1),
        )

        self.assertTrue(
            RoleGovernanceService.can_manage_assignment(
                actor_role,
                assignment,
            )
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_manage_assignment_returns_false_for_unmanaged_role(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = True

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        assignment = self.make_assignment(
            "ROOM_ADMIN",
            room=self.make_room(id=1),
        )

        self.assertFalse(
            RoleGovernanceService.can_manage_assignment(
                actor_role,
                assignment,
            )
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_manage_assignment_returns_false_for_assignment_outside_scope(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = False

        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )
        assignment = self.make_assignment(
            "ROOM_VIEWER",
            room=self.make_room(id=2),
        )

        self.assertFalse(
            RoleGovernanceService.can_manage_assignment(
                actor_role,
                assignment,
            )
        )

    def test_can_manage_assignment_returns_false_without_actor_role(self):
        assignment = self.make_assignment(
            "ROOM_VIEWER",
            room=self.make_room(id=1),
        )

        self.assertFalse(
            RoleGovernanceService.can_manage_assignment(
                None,
                assignment,
            )
        )

    def test_can_manage_assignment_returns_false_without_assignment(self):
        actor_role = self.make_actor_role(
            "ROOM_ADMIN",
            room_id=1,
        )

        self.assertFalse(
            RoleGovernanceService.can_manage_assignment(
                actor_role,
                None,
            )
        )