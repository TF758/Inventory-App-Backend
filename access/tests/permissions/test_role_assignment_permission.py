# access/tests/test_role_assignment_permission.py

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.permissions.role_assignment import RoleAssignmentPermission




class RoleAssignmentPermissionTests(SimpleTestCase):
    """
    Canonical CRUD scoped-permission tests.

    RoleAssignmentPermission is used here as the representative test case
    for permission classes that follow the standard CRUD + object-scope
    pattern:

        - request method maps to a permission code
        - object checks require an active role
        - object checks require base permission approval
        - object checks delegate scope to the correct ScopeService method

    This same structure is used by other simple scoped permissions such as:

        - AssetPermission
        - UserPlacementPermission

    We do not duplicate the same full test suite for every class because
    ScopedPermission already tests permission-code resolution, and the
    service tests already cover the actual access/scope rules.

    Additional permission classes only need their own tests when they add
    custom behavior, such as:

        - action-based permission maps
        - custom object resolution
        - creation-time scope validation
        - move/transfer business rules
        - identity/self-service logic

    It intentionally does not retest:

        - AccessService database behavior
        - ScopeService role/scope combinations
        - RoleGovernanceService
        - serializers
        - API routing
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        return SimpleNamespace(
            role="ROOM_VIEWER",
            room=SimpleNamespace(id=1),
            location=None,
            department=None,
        )

    # ------------------------------------------------------------------
    # Method map
    # ------------------------------------------------------------------

    def test_method_map_returns_expected_permission_codes(self):
        permission = RoleAssignmentPermission()
        view = self.make_view()

        cases = [
            ("GET", ["role_assignments.view"]),
            ("POST", ["role_assignments.create"]),
            ("PUT", ["role_assignments.update"]),
            ("PATCH", ["role_assignments.update"]),
            ("DELETE", ["role_assignments.delete"]),
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

    @patch.object(RoleAssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_role_assignment")
    def test_has_object_permission_returns_false_without_active_role(
        self,
        mock_can_access_role_assignment,
        mock_has_permission,
    ):
        permission = RoleAssignmentPermission()
        user = self.make_user(
            active_role=None,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        assignment = self.make_assignment()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                assignment,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_role_assignment.assert_not_called()

    @patch.object(RoleAssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_role_assignment")
    def test_has_object_permission_returns_false_when_base_permission_denied(
        self,
        mock_can_access_role_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        permission = RoleAssignmentPermission()
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
        mock_can_access_role_assignment.assert_not_called()

    @patch.object(RoleAssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_role_assignment")
    def test_has_object_permission_returns_false_when_scope_denied(
        self,
        mock_can_access_role_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_role_assignment.return_value = False

        permission = RoleAssignmentPermission()
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
        mock_can_access_role_assignment.assert_called_once_with(
            active_role,
            assignment,
        )

    @patch.object(RoleAssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_role_assignment")
    def test_has_object_permission_returns_true_when_permission_and_scope_allowed(
        self,
        mock_can_access_role_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_role_assignment.return_value = True

        permission = RoleAssignmentPermission()
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
        mock_can_access_role_assignment.assert_called_once_with(
            active_role,
            assignment,
        )

    @patch.object(RoleAssignmentPermission, "has_permission")
    @patch("access.services.scope.ScopeService.can_access_role_assignment")
    def test_has_object_permission_delegates_exact_actor_and_object_to_scope_service(
        self,
        mock_can_access_role_assignment,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_role_assignment.return_value = True

        permission = RoleAssignmentPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=10,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "PATCH",
            user=user,
        )
        view = self.make_view()
        assignment = self.make_assignment()

        result = permission.has_object_permission(
            request,
            view,
            assignment,
        )

        self.assertTrue(result)
        mock_can_access_role_assignment.assert_called_once_with(
            active_role,
            assignment,
        )