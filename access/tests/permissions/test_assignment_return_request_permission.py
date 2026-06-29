# access/tests/permissions/test_assignment_permissions.py

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.permissions.assignments import AssignmentPermission
from access.permissions.returns import ReturnRequestPermission



class AssignmentPermissionTests(SimpleTestCase):
    """
    Thin wiring tests for AssignmentPermission.

    This permission uses view.action-based mapping and delegates
    object scope checks to ScopeService.can_access_assignment.
    """

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

    def make_view(
        self,
        *,
        action=None,
    ):
        view = SimpleNamespace()

        if action is not None:
            view.action = action

        return view

    def make_assignment(self):
        return SimpleNamespace(id=1)

    # ------------------------------------------------------------------
    # Action map
    # ------------------------------------------------------------------

    def test_action_map_returns_expected_permission_codes(self):
        permission = AssignmentPermission()
        request = self.make_request("GET")

        cases = [
            ("list", ["assignments.view"]),
            ("retrieve", ["assignments.view"]),
        ]

        for action, expected in cases:
            with self.subTest(action=action):
                view = self.make_view(action=action)

                self.assertEqual(
                    permission.get_required_permissions(
                        request,
                        view,
                    ),
                    expected,
                )

    def test_unmapped_action_returns_empty_permissions(self):
        permission = AssignmentPermission()
        request = self.make_request("GET")
        view = self.make_view(action="unknown")

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [],
        )

    # ------------------------------------------------------------------
    # Object permission
    # ------------------------------------------------------------------

    @patch.object(AssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_assignment")
    def test_has_object_permission_returns_false_without_active_role(
        self,
        mock_can_access_assignment,
        mock_has_permission,
    ):
        permission = AssignmentPermission()
        user = self.make_user(active_role=None)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        assignment = self.make_assignment()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                assignment,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_assignment.assert_not_called()

    @patch.object(AssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_assignment")
    def test_has_object_permission_returns_false_when_base_permission_denied(
        self,
        mock_can_access_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        permission = AssignmentPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(active_role=active_role)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        assignment = self.make_assignment()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                assignment,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_assignment.assert_not_called()

    @patch.object(AssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_assignment")
    def test_has_object_permission_returns_false_when_scope_denied(
        self,
        mock_can_access_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_assignment.return_value = False

        permission = AssignmentPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(active_role=active_role)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        assignment = self.make_assignment()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                assignment,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_assignment.assert_called_once_with(
            active_role,
            assignment,
        )

    @patch.object(AssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_assignment")
    def test_has_object_permission_returns_true_when_permission_and_scope_allowed(
        self,
        mock_can_access_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_assignment.return_value = True

        permission = AssignmentPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        user = self.make_user(active_role=active_role)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        assignment = self.make_assignment()

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                assignment,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_assignment.assert_called_once_with(
            active_role,
            assignment,
        )


class ReturnRequestPermissionTests(SimpleTestCase):
    """
    Thin wiring tests for ReturnRequestPermission.

    This permission uses view.action-based mapping and delegates
    object scope checks to ScopeService.can_access_return_request.
    """

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

    def make_view(
        self,
        *,
        action=None,
    ):
        view = SimpleNamespace()

        if action is not None:
            view.action = action

        return view

    def make_return_request(self):
        return SimpleNamespace(id=1)

    # ------------------------------------------------------------------
    # Action map
    # ------------------------------------------------------------------

    def test_action_map_returns_expected_permission_codes(self):
        permission = ReturnRequestPermission()
        request = self.make_request("GET")

        cases = [
            ("list", ["returns.view"]),
            ("retrieve", ["returns.view"]),
            ("pending", ["returns.view"]),
            ("approve", ["returns.process"]),
            ("deny", ["returns.process"]),
            ("process", ["returns.process"]),
        ]

        for action, expected in cases:
            with self.subTest(action=action):
                view = self.make_view(action=action)

                self.assertEqual(
                    permission.get_required_permissions(
                        request,
                        view,
                    ),
                    expected,
                )

    def test_unmapped_action_returns_empty_permissions(self):
        permission = ReturnRequestPermission()
        request = self.make_request("GET")
        view = self.make_view(action="unknown")

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [],
        )

    # ------------------------------------------------------------------
    # Object permission
    # ------------------------------------------------------------------

    @patch.object(ReturnRequestPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_return_request")
    def test_has_object_permission_returns_false_without_active_role(
        self,
        mock_can_access_return_request,
        mock_has_permission,
    ):
        permission = ReturnRequestPermission()
        user = self.make_user(active_role=None)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        return_request = self.make_return_request()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                return_request,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_return_request.assert_not_called()

    @patch.object(ReturnRequestPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_return_request")
    def test_has_object_permission_returns_false_when_base_permission_denied(
        self,
        mock_can_access_return_request,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        permission = ReturnRequestPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(active_role=active_role)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        return_request = self.make_return_request()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                return_request,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_return_request.assert_not_called()

    @patch.object(ReturnRequestPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_return_request")
    def test_has_object_permission_returns_false_when_scope_denied(
        self,
        mock_can_access_return_request,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_return_request.return_value = False

        permission = ReturnRequestPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(active_role=active_role)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        return_request = self.make_return_request()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                return_request,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_return_request.assert_called_once_with(
            active_role,
            return_request,
        )

    @patch.object(ReturnRequestPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_return_request")
    def test_has_object_permission_returns_true_when_permission_and_scope_allowed(
        self,
        mock_can_access_return_request,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_return_request.return_value = True

        permission = ReturnRequestPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        user = self.make_user(active_role=active_role)
        request = self.make_request(user=user)
        view = self.make_view(action="retrieve")
        return_request = self.make_return_request()

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                return_request,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_return_request.assert_called_once_with(
            active_role,
            return_request,
        )