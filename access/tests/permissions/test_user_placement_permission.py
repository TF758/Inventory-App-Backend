from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.permissions.users import UserPlacementPermission


class UserPlacementPermissionTests(SimpleTestCase):
    """
    Thin wiring tests for UserPlacementPermission.

    UserPlacementPermission follows the standard CRUD scoped-permission
    pattern, but has one extra object-level requirement:

        - the placement object must have a room

    These tests prove:

        - request method maps to the correct permission code
        - object checks require an active role
        - object checks reject placements without a room
        - object checks require base permission approval
        - object checks delegate room scope to ScopeService.can_access_room

    It intentionally does not retest:

        - AccessService database behavior
        - ScopeService role/scope combinations
        - serializers
        - API routing
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_role_assignment(
        self,
        role="ROOM_ADMIN",
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

    def make_user(
        self,
        *,
        active_role=None,
        is_authenticated=True,
    ):
        return SimpleNamespace(
            active_role=active_role,
            is_authenticated=is_authenticated,
        )

    def make_request(
        self,
        method="GET",
        *,
        user=None,
        data=None,
    ):
        return SimpleNamespace(
            method=method,
            user=user,
            data=data or {},
        )

    def make_view(self):
        return SimpleNamespace()

    def make_room(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    def make_placement(
        self,
        *,
        room=None,
    ):
        return SimpleNamespace(
            id=1,
            room=room,
        )

    # ------------------------------------------------------------------
    # Method map
    # ------------------------------------------------------------------

    def test_method_map_returns_expected_permission_codes(self):
        permission = UserPlacementPermission()
        view = self.make_view()

        cases = [
            ("GET", ["user_placements.view"]),
            ("POST", ["user_placements.create"]),
            ("PUT", ["user_placements.update"]),
            ("PATCH", ["user_placements.update"]),
            ("DELETE", ["user_placements.delete"]),
        ]

        for method, expected in cases:
            with self.subTest(method=method):
                request = self.make_request(method)

                self.assertEqual(
                    permission.get_required_permissions(
                        request,
                        view,
                    ),
                    expected,
                )

    # ------------------------------------------------------------------
    # Object permission
    # ------------------------------------------------------------------

    @patch.object(UserPlacementPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_has_object_permission_returns_false_without_active_role(
        self,
        mock_can_access_room,
        mock_has_permission,
    ):
        permission = UserPlacementPermission()
        user = self.make_user(
            active_role=None,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        placement = self.make_placement(
            room=self.make_room(id=1),
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                placement,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_room.assert_not_called()

    @patch.object(UserPlacementPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_has_object_permission_returns_false_when_placement_has_no_room(
        self,
        mock_can_access_room,
        mock_has_permission,
    ):
        permission = UserPlacementPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        placement = self.make_placement(
            room=None,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                placement,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_room.assert_not_called()

    @patch.object(UserPlacementPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_has_object_permission_returns_false_when_base_permission_denied(
        self,
        mock_can_access_room,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        permission = UserPlacementPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        room = self.make_room(id=1)
        placement = self.make_placement(
            room=room,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                placement,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_room.assert_not_called()

    @patch.object(UserPlacementPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_has_object_permission_returns_false_when_scope_denied(
        self,
        mock_can_access_room,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = False

        permission = UserPlacementPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        room = self.make_room(id=2)
        placement = self.make_placement(
            room=room,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                placement,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_room.assert_called_once_with(
            active_role,
            room,
        )

    @patch.object(UserPlacementPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_has_object_permission_returns_true_when_permission_and_scope_allowed(
        self,
        mock_can_access_room,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        permission = UserPlacementPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "PATCH",
            user=user,
        )
        view = self.make_view()
        room = self.make_room(id=1)
        placement = self.make_placement(
            room=room,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                placement,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_room.assert_called_once_with(
            active_role,
            room,
        )

    @patch.object(UserPlacementPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_room")
    def test_has_object_permission_delegates_exact_active_role_and_room_to_scope_service(
        self,
        mock_can_access_room,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        permission = UserPlacementPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=10,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "DELETE",
            user=user,
        )
        view = self.make_view()
        room = self.make_room(id=99)
        placement = self.make_placement(
            room=room,
        )

        result = permission.has_object_permission(
            request,
            view,
            placement,
        )

        self.assertTrue(result)
        mock_can_access_room.assert_called_once_with(
            active_role,
            room,
        )