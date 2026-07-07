# access/tests/test_scope_service.py

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from assignments.models.asset_assignment import (
    ReturnRequest,
    ReturnRequestItem,
)
from access.services.scope import (
    ScopeService,
    UserScopeService,
)


class ScopeServiceTests(SimpleTestCase):
    """
    Unit tests for ScopeService.

    ScopeService answers:

        - Can this active role access this room?
        - Can this active role access an object by resolving it to a room?

    These tests intentionally avoid the database.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_department(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    def make_location(
        self,
        id=1,
        department_id=1,
        department=None,
    ):
        return SimpleNamespace(
            id=id,
            department_id=department_id,
            department=department,
        )

    def make_room(
        self,
        id=1,
        location=None,
    ):
        return SimpleNamespace(
            id=id,
            location=location,
            location_id=getattr(location, "id", None),
        )

    def make_role_assignment(
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

    def make_scoped_assignment(
        self,
        *,
        role="ROOM_VIEWER",
        room=None,
        location=None,
        department=None,
    ):
        return SimpleNamespace(
            role=role,
            room=room,
            location=location,
            department=department,
            room_id=getattr(room, "id", None),
            location_id=getattr(location, "id", None),
            department_id=getattr(department, "id", None),
        )

    # ------------------------------------------------------------------
    # can_access_room base behavior
    # ------------------------------------------------------------------

    def test_can_access_room_returns_false_without_role_assignment(self):
        room = self.make_room(
            location=self.make_location(),
        )

        self.assertFalse(
            ScopeService.can_access_room(
                None,
                room,
            )
        )

    def test_can_access_room_returns_false_without_room(self):
        role_assignment = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )

        self.assertFalse(
            ScopeService.can_access_room(
                role_assignment,
                None,
            )
        )

    def test_unknown_role_cannot_access_room(self):
        role_assignment = self.make_role_assignment(
            "UNKNOWN_ROLE",
            room_id=1,
        )
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        self.assertFalse(
            ScopeService.can_access_room(
                role_assignment,
                room,
            )
        )

    # ------------------------------------------------------------------
    # SITE_ADMIN room access
    # ------------------------------------------------------------------

    def test_site_admin_can_access_any_room(self):
        role_assignment = self.make_role_assignment(
            "SITE_ADMIN",
        )
        room = self.make_room(
            id=99,
            location=self.make_location(
                id=99,
                department_id=99,
            ),
        )

        self.assertTrue(
            ScopeService.can_access_room(
                role_assignment,
                room,
            )
        )

    # ------------------------------------------------------------------
    # Department role room access
    # ------------------------------------------------------------------

    def test_department_roles_can_access_rooms_inside_department(self):
        location = self.make_location(
            id=10,
            department_id=1,
        )
        room = self.make_room(
            id=100,
            location=location,
        )

        for role in [
            "DEPARTMENT_ADMIN",
            "DEPARTMENT_VIEWER",
        ]:
            with self.subTest(role=role):
                role_assignment = self.make_role_assignment(
                    role,
                    department_id=1,
                )

                self.assertTrue(
                    ScopeService.can_access_room(
                        role_assignment,
                        room,
                    )
                )

    def test_department_roles_cannot_access_rooms_outside_department(self):
        location = self.make_location(
            id=10,
            department_id=2,
        )
        room = self.make_room(
            id=100,
            location=location,
        )

        for role in [
            "DEPARTMENT_ADMIN",
            "DEPARTMENT_VIEWER",
        ]:
            with self.subTest(role=role):
                role_assignment = self.make_role_assignment(
                    role,
                    department_id=1,
                )

                self.assertFalse(
                    ScopeService.can_access_room(
                        role_assignment,
                        room,
                    )
                )

    def test_department_role_cannot_access_room_without_location(self):
        role_assignment = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        room = self.make_room(
            id=1,
            location=None,
        )

        self.assertFalse(
            ScopeService.can_access_room(
                role_assignment,
                room,
            )
        )

    def test_department_role_cannot_access_room_with_location_without_department_match(self):
        location = self.make_location(
            id=10,
            department_id=None,
        )
        room = self.make_room(
            id=1,
            location=location,
        )
        role_assignment = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )

        self.assertFalse(
            ScopeService.can_access_room(
                role_assignment,
                room,
            )
        )

    # ------------------------------------------------------------------
    # Location role room access
    # ------------------------------------------------------------------

    def test_location_roles_can_access_rooms_inside_location(self):
        location = self.make_location(
            id=10,
            department_id=1,
        )
        room = self.make_room(
            id=100,
            location=location,
        )

        for role in [
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
        ]:
            with self.subTest(role=role):
                role_assignment = self.make_role_assignment(
                    role,
                    location_id=10,
                )

                self.assertTrue(
                    ScopeService.can_access_room(
                        role_assignment,
                        room,
                    )
                )

    def test_location_roles_cannot_access_rooms_outside_location(self):
        location = self.make_location(
            id=11,
            department_id=1,
        )
        room = self.make_room(
            id=100,
            location=location,
        )

        for role in [
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
        ]:
            with self.subTest(role=role):
                role_assignment = self.make_role_assignment(
                    role,
                    location_id=10,
                )

                self.assertFalse(
                    ScopeService.can_access_room(
                        role_assignment,
                        room,
                    )
                )

    def test_location_role_cannot_access_room_without_location(self):
        role_assignment = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        room = self.make_room(
            id=100,
            location=None,
        )

        self.assertFalse(
            ScopeService.can_access_room(
                role_assignment,
                room,
            )
        )

    # ------------------------------------------------------------------
    # Room role room access
    # ------------------------------------------------------------------

    def test_room_roles_can_access_exact_room(self):
        room = self.make_room(
            id=100,
            location=self.make_location(),
        )

        for role in [
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        ]:
            with self.subTest(role=role):
                role_assignment = self.make_role_assignment(
                    role,
                    room_id=100,
                )

                self.assertTrue(
                    ScopeService.can_access_room(
                        role_assignment,
                        room,
                    )
                )

    def test_room_roles_cannot_access_other_room(self):
        room = self.make_room(
            id=200,
            location=self.make_location(),
        )

        for role in [
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        ]:
            with self.subTest(role=role):
                role_assignment = self.make_role_assignment(
                    role,
                    room_id=100,
                )

                self.assertFalse(
                    ScopeService.can_access_room(
                        role_assignment,
                        room,
                    )
                )

    # ------------------------------------------------------------------
    # Room resolvers
    # ------------------------------------------------------------------

    def test_get_asset_room_returns_asset_room(self):
        room = self.make_room(
            location=self.make_location(),
        )
        asset = SimpleNamespace(
            room=room,
        )

        self.assertEqual(
            ScopeService.get_asset_room(asset),
            room,
        )

    def test_get_asset_room_returns_none_when_missing_room(self):
        asset = SimpleNamespace()

        self.assertIsNone(
            ScopeService.get_asset_room(asset)
        )

    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_get_user_room_returns_current_placement_room(
        self,
        mock_filter,
    ):
        user = SimpleNamespace(id=1)
        room = self.make_room(
            location=self.make_location(),
        )
        placement = SimpleNamespace(
            room=room,
        )

        (
            mock_filter.return_value
            .select_related.return_value
            .first.return_value
        ) = placement

        self.assertEqual(
            ScopeService.get_user_room(user),
            room,
        )

        mock_filter.assert_called_once_with(
            user=user,
            is_current=True,
        )

    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_get_user_room_returns_none_without_current_placement(
        self,
        mock_filter,
    ):
        user = SimpleNamespace(id=1)

        (
            mock_filter.return_value
            .select_related.return_value
            .first.return_value
        ) = None

        self.assertIsNone(
            ScopeService.get_user_room(user)
        )

    @patch("access.services.scope.ScopeService.get_user_room")
    def test_get_assignment_room_uses_assignment_user(
        self,
        mock_get_user_room,
    ):
        user = SimpleNamespace(id=1)
        room = self.make_room(
            location=self.make_location(),
        )
        assignment = SimpleNamespace(
            user=user,
        )

        mock_get_user_room.return_value = room

        self.assertEqual(
            ScopeService.get_assignment_room(assignment),
            room,
        )

        mock_get_user_room.assert_called_once_with(user)

    @patch("access.services.scope.ScopeService.get_user_room")
    def test_get_assignment_room_returns_none_without_user(
        self,
        mock_get_user_room,
    ):
        assignment = SimpleNamespace(
            user=None,
        )

        self.assertIsNone(
            ScopeService.get_assignment_room(assignment)
        )

        mock_get_user_room.assert_not_called()

    def test_get_return_request_room_from_return_request_item(self):
        room = self.make_room(
            location=self.make_location(),
        )

        item = Mock(spec=ReturnRequestItem)
        item.room = room

        self.assertEqual(
            ScopeService.get_return_request_room(item),
            room,
        )

    def test_get_return_request_room_from_return_request_first_item(self):
        room = self.make_room(
            location=self.make_location(),
        )
        item = SimpleNamespace(
            room=room,
        )

        return_request = Mock(spec=ReturnRequest)
        return_request.items = Mock()
        (
            return_request.items
            .select_related.return_value
            .first.return_value
        ) = item

        self.assertEqual(
            ScopeService.get_return_request_room(return_request),
            room,
        )

        return_request.items.select_related.assert_called_once_with(
            "room",
        )

    def test_get_return_request_room_returns_none_for_return_request_without_items(self):
        return_request = Mock(spec=ReturnRequest)
        return_request.items = Mock()
        (
            return_request.items
            .select_related.return_value
            .first.return_value
        ) = None

        self.assertIsNone(
            ScopeService.get_return_request_room(return_request)
        )

    def test_get_return_request_room_returns_none_for_unknown_object(self):
        self.assertIsNone(
            ScopeService.get_return_request_room(
                SimpleNamespace(),
            )
        )

    # ------------------------------------------------------------------
    # Convenience checks
    # ------------------------------------------------------------------

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_access_asset_resolves_asset_room(
        self,
        mock_can_access_room,
    ):
        role_assignment = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )
        asset = SimpleNamespace(
            room=room,
        )

        mock_can_access_room.return_value = True

        self.assertTrue(
            ScopeService.can_access_asset(
                role_assignment,
                asset,
            )
        )

        mock_can_access_room.assert_called_once_with(
            role_assignment,
            room,
        )

    @patch("access.services.scope.ScopeService.get_user_room")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_access_user_resolves_user_room(
        self,
        mock_can_access_room,
        mock_get_user_room,
    ):
        role_assignment = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = SimpleNamespace(id=1)
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        mock_get_user_room.return_value = room
        mock_can_access_room.return_value = True

        self.assertTrue(
            ScopeService.can_access_user(
                role_assignment,
                user,
            )
        )

        mock_get_user_room.assert_called_once_with(user)
        mock_can_access_room.assert_called_once_with(
            role_assignment,
            room,
        )

    @patch("access.services.scope.ScopeService.get_assignment_room")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_access_assignment_resolves_assignment_room(
        self,
        mock_can_access_room,
        mock_get_assignment_room,
    ):
        role_assignment = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        assignment = SimpleNamespace(id=1)
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        mock_get_assignment_room.return_value = room
        mock_can_access_room.return_value = True

        self.assertTrue(
            ScopeService.can_access_assignment(
                role_assignment,
                assignment,
            )
        )

        mock_get_assignment_room.assert_called_once_with(
            assignment,
        )
        mock_can_access_room.assert_called_once_with(
            role_assignment,
            room,
        )

    @patch("access.services.scope.ScopeService.get_return_request_room")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_access_return_request_resolves_return_request_room(
        self,
        mock_can_access_room,
        mock_get_return_request_room,
    ):
        role_assignment = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        return_request = SimpleNamespace(id=1)
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        mock_get_return_request_room.return_value = room
        mock_can_access_room.return_value = True

        self.assertTrue(
            ScopeService.can_access_return_request(
                role_assignment,
                return_request,
            )
        )

        mock_get_return_request_room.assert_called_once_with(
            return_request,
        )
        mock_can_access_room.assert_called_once_with(
            role_assignment,
            room,
        )

    # ------------------------------------------------------------------
    # Role assignment scope
    # ------------------------------------------------------------------

    def test_can_access_role_assignment_returns_false_without_actor_role(self):
        assignment = self.make_scoped_assignment(
            room=self.make_room(
                id=1,
                location=self.make_location(),
            ),
        )

        self.assertFalse(
            ScopeService.can_access_role_assignment(
                None,
                assignment,
            )
        )

    def test_can_access_role_assignment_returns_false_without_assignment(self):
        actor_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )

        self.assertFalse(
            ScopeService.can_access_role_assignment(
                actor_role,
                None,
            )
        )

    @patch("access.services.scope.ScopeService.can_access_room")
    def test_can_access_role_assignment_with_room_scope_delegates_to_room_access(
        self,
        mock_can_access_room,
    ):
        role_assignment = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )
        assignment = self.make_scoped_assignment(
            room=room,
        )

        mock_can_access_room.return_value = True

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

        mock_can_access_room.assert_called_once_with(
            role_assignment,
            room,
        )

    def test_site_admin_can_access_location_scoped_role_assignment(self):
        role_assignment = self.make_role_assignment(
            "SITE_ADMIN",
        )
        location = self.make_location(
            id=10,
            department_id=2,
        )
        assignment = self.make_scoped_assignment(
            location=location,
        )

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_department_actor_can_access_location_scoped_assignment_inside_department(self):
        role_assignment = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        location = self.make_location(
            id=10,
            department_id=1,
        )
        assignment = self.make_scoped_assignment(
            location=location,
        )

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_department_actor_cannot_access_location_scoped_assignment_outside_department(self):
        role_assignment = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        location = self.make_location(
            id=10,
            department_id=2,
        )
        assignment = self.make_scoped_assignment(
            location=location,
        )

        self.assertFalse(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_location_actor_can_access_own_location_scoped_assignment(self):
        role_assignment = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        location = self.make_location(
            id=10,
            department_id=1,
        )
        assignment = self.make_scoped_assignment(
            location=location,
        )

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_location_actor_cannot_access_other_location_scoped_assignment(self):
        role_assignment = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        location = self.make_location(
            id=11,
            department_id=1,
        )
        assignment = self.make_scoped_assignment(
            location=location,
        )

        self.assertFalse(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_site_admin_can_access_department_scoped_role_assignment(self):
        role_assignment = self.make_role_assignment(
            "SITE_ADMIN",
        )
        department = self.make_department(
            id=99,
        )
        assignment = self.make_scoped_assignment(
            department=department,
        )

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_department_actor_can_access_own_department_scoped_assignment(self):
        role_assignment = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        department = self.make_department(
            id=1,
        )
        assignment = self.make_scoped_assignment(
            department=department,
        )

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_department_actor_cannot_access_other_department_scoped_assignment(self):
        role_assignment = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        department = self.make_department(
            id=2,
        )
        assignment = self.make_scoped_assignment(
            department=department,
        )

        self.assertFalse(
            ScopeService.can_access_role_assignment(
                role_assignment,
                assignment,
            )
        )

    def test_only_site_admin_can_access_site_level_role_assignment(self):
        site_admin = self.make_role_assignment(
            "SITE_ADMIN",
        )
        department_admin = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )

        site_level_assignment = self.make_scoped_assignment()

        self.assertTrue(
            ScopeService.can_access_role_assignment(
                site_admin,
                site_level_assignment,
            )
        )
        self.assertFalse(
            ScopeService.can_access_role_assignment(
                department_admin,
                site_level_assignment,
            )
        )


class UserScopeServiceTests(SimpleTestCase):
    """
    Unit tests for UserScopeService.

    UserScopeService answers whether an actor can access a user through:

        - the user's current placement
        - the user's role assignments
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_department(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    def make_location(
        self,
        id=1,
        department_id=1,
    ):
        return SimpleNamespace(
            id=id,
            department_id=department_id,
        )

    def make_room(
        self,
        id=1,
        location=None,
    ):
        return SimpleNamespace(
            id=id,
            location=location,
            location_id=getattr(location, "id", None),
        )

    def make_role_assignment(
        self,
        role,
        *,
        department_id=None,
        location_id=None,
        room_id=None,
        room=None,
        location=None,
        department=None,
    ):
        return SimpleNamespace(
            role=role,
            department_id=department_id,
            location_id=location_id,
            room_id=room_id,
            room=room,
            location=location,
            department=department,
        )

    def make_user(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    def make_placement(self, room):
        return SimpleNamespace(
            room=room,
        )

    def set_queryset_result(
        self,
        mock_filter,
        result,
    ):
        mock_filter.return_value.select_related.return_value = result

    # ------------------------------------------------------------------
    # Base behavior
    # ------------------------------------------------------------------

    def test_returns_false_without_role_assignment(self):
        user = self.make_user()

        self.assertFalse(
            UserScopeService.can_access_user(
                None,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_site_admin_can_access_any_user_without_queries(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        role_assignment = self.make_role_assignment(
            "SITE_ADMIN",
        )
        user = self.make_user()

        self.assertTrue(
            UserScopeService.can_access_user(
                role_assignment,
                user,
            )
        )

        mock_placement_filter.assert_not_called()
        mock_role_filter.assert_not_called()

    # ------------------------------------------------------------------
    # Placement scope
    # ------------------------------------------------------------------

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_true_when_current_placement_is_inside_scope(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user()
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        self.set_queryset_result(
            mock_placement_filter,
            [
                self.make_placement(room),
            ],
        )
        self.set_queryset_result(
            mock_role_filter,
            [],
        )

        self.assertTrue(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_continues_to_role_assignments_when_current_placements_are_outside_scope(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user()

        outside_room = self.make_room(
            id=2,
            location=self.make_location(),
        )
        inside_room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        self.set_queryset_result(
            mock_placement_filter,
            [
                self.make_placement(outside_room),
            ],
        )
        self.set_queryset_result(
            mock_role_filter,
            [
                self.make_role_assignment(
                    "ROOM_VIEWER",
                    room=inside_room,
                    room_id=inside_room.id,
                ),
            ],
        )

        self.assertTrue(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_false_when_placements_and_roles_are_outside_scope(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user()

        outside_room = self.make_room(
            id=2,
            location=self.make_location(),
        )

        self.set_queryset_result(
            mock_placement_filter,
            [
                self.make_placement(outside_room),
            ],
        )
        self.set_queryset_result(
            mock_role_filter,
            [],
        )

        self.assertFalse(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    # ------------------------------------------------------------------
    # Role assignment scope
    # ------------------------------------------------------------------

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_true_when_user_room_role_is_inside_actor_scope(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user()
        room = self.make_room(
            id=1,
            location=self.make_location(),
        )

        self.set_queryset_result(
            mock_placement_filter,
            [],
        )
        self.set_queryset_result(
            mock_role_filter,
            [
                self.make_role_assignment(
                    "ROOM_VIEWER",
                    room=room,
                    room_id=room.id,
                ),
            ],
        )

        self.assertTrue(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_true_when_user_location_role_is_inside_actor_location(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        user = self.make_user()
        location = self.make_location(
            id=10,
            department_id=1,
        )

        self.set_queryset_result(
            mock_placement_filter,
            [],
        )
        self.set_queryset_result(
            mock_role_filter,
            [
                self.make_role_assignment(
                    "LOCATION_VIEWER",
                    location=location,
                    location_id=location.id,
                ),
            ],
        )

        self.assertTrue(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_true_when_user_location_role_is_inside_actor_department(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user()
        location = self.make_location(
            id=10,
            department_id=1,
        )

        self.set_queryset_result(
            mock_placement_filter,
            [],
        )
        self.set_queryset_result(
            mock_role_filter,
            [
                self.make_role_assignment(
                    "LOCATION_VIEWER",
                    location=location,
                    location_id=location.id,
                ),
            ],
        )

        self.assertTrue(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_true_when_user_department_role_is_inside_actor_department(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user()
        department = self.make_department(
            id=1,
        )

        self.set_queryset_result(
            mock_placement_filter,
            [],
        )
        self.set_queryset_result(
            mock_role_filter,
            [
                self.make_role_assignment(
                    "DEPARTMENT_VIEWER",
                    department=department,
                    department_id=department.id,
                ),
            ],
        )

        self.assertTrue(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )

    @patch("access.services.scope.RoleAssignment.objects.filter")
    @patch("access.services.scope.UserPlacement.objects.filter")
    def test_returns_false_when_user_role_assignments_are_outside_actor_scope(
        self,
        mock_placement_filter,
        mock_role_filter,
    ):
        actor_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user()

        outside_department = self.make_department(
            id=2,
        )
        outside_location = self.make_location(
            id=10,
            department_id=2,
        )
        outside_room = self.make_room(
            id=100,
            location=outside_location,
        )

        self.set_queryset_result(
            mock_placement_filter,
            [],
        )
        self.set_queryset_result(
            mock_role_filter,
            [
                self.make_role_assignment(
                    "ROOM_VIEWER",
                    room=outside_room,
                    room_id=outside_room.id,
                ),
                self.make_role_assignment(
                    "LOCATION_VIEWER",
                    location=outside_location,
                    location_id=outside_location.id,
                ),
                self.make_role_assignment(
                    "DEPARTMENT_VIEWER",
                    department=outside_department,
                    department_id=outside_department.id,
                ),
            ],
        )

        self.assertFalse(
            UserScopeService.can_access_user(
                actor_role,
                user,
            )
        )