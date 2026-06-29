# access/tests/test_scoped_permission.py

from types import SimpleNamespace
from unittest.mock import call, patch

from django.test import SimpleTestCase

from access.permissions.scoped import ScopedPermission


class ScopedPermissionTests(SimpleTestCase):
    """
    Unit tests for ScopedPermission.

    ScopedPermission extends RequiresPermission by resolving permission
    codes from request.method using permission_map.

    These tests intentionally do not test:
        - database-backed permissions
        - object scope
        - serializers
        - API routing
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_request(
        self,
        method="GET",
        *,
        user=None,
    ):
        return SimpleNamespace(
            method=method,
            user=user,
        )

    def make_user(
        self,
        *,
        is_authenticated=True,
    ):
        return SimpleNamespace(
            is_authenticated=is_authenticated,
        )

    def make_view(
        self,
        *,
        action=None,
        required_permission=None,
        required_permissions=None,
    ):
        view = SimpleNamespace()

        if action is not None:
            view.action = action

        if required_permission is not None:
            view.required_permission = required_permission

        if required_permissions is not None:
            view.required_permissions = required_permissions

        return view

    # ------------------------------------------------------------------
    # permission_map lookup
    # ------------------------------------------------------------------

    def test_get_required_permissions_returns_single_permission_from_method_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "GET": "assets.view",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
            ],
        )

    def test_get_required_permissions_returns_list_permission_from_method_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": [
                    "assets.create",
                    "assets.update",
                ],
            }

        permission = TestPermission()
        request = self.make_request("POST")
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.create",
                "assets.update",
            ],
        )

    def test_get_required_permissions_returns_tuple_permission_from_method_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "PATCH": (
                    "assets.update",
                    "assets.change_status",
                ),
            }

        permission = TestPermission()
        request = self.make_request("PATCH")
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.update",
                "assets.change_status",
            ],
        )

    def test_get_required_permissions_returns_set_permission_from_method_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "DELETE": {
                    "assets.delete",
                    "audit.write",
                },
            }

        permission = TestPermission()
        request = self.make_request("DELETE")
        view = self.make_view()

        self.assertEqual(
            set(
                permission.get_required_permissions(
                    request,
                    view,
                )
            ),
            {
                "assets.delete",
                "audit.write",
            },
        )

    def test_get_required_permissions_returns_empty_list_for_empty_permission_list(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": [],
            }

        permission = TestPermission()
        request = self.make_request("POST")
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [],
        )

    # ------------------------------------------------------------------
    # Fallback behavior
    # ------------------------------------------------------------------

    def test_get_required_permissions_falls_back_to_view_required_permission_when_method_missing(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": "assets.create",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view(
            required_permission="assets.view",
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
            ],
        )

    def test_get_required_permissions_falls_back_to_view_required_permissions_when_method_missing(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": "assets.create",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view(
            required_permissions=[
                "assets.view",
                "assets.update",
            ],
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
                "assets.update",
            ],
        )

    def test_get_required_permissions_falls_back_to_class_required_permission_when_method_missing(self):
        class TestPermission(ScopedPermission):
            required_permission = "assets.view"

            permission_map = {
                "POST": "assets.create",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
            ],
        )

    def test_get_required_permissions_returns_empty_when_method_missing_and_no_fallback(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": "assets.create",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [],
        )

    def test_permission_map_takes_precedence_over_view_required_permission(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "GET": "assets.view",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view(
            required_permission="reports.view",
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
            ],
        )

    # ------------------------------------------------------------------
    # inherited has_permission behavior
    # ------------------------------------------------------------------

    @patch("access.permissions.base.AccessService.has_permission")
    def test_has_permission_uses_permission_map_permission(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        class TestPermission(ScopedPermission):
            permission_map = {
                "GET": "assets.view",
            }

        user = self.make_user()
        permission = TestPermission()
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_called_once_with(
            user,
            "assets.view",
        )

    @patch("access.permissions.base.AccessService.has_permission")
    def test_has_permission_returns_false_when_mapped_permission_denied(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": "assets.create",
            }

        user = self.make_user()
        permission = TestPermission()
        request = self.make_request(
            "POST",
            user=user,
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_called_once_with(
            user,
            "assets.create",
        )

    @patch("access.permissions.base.AccessService.has_permission")
    def test_has_permission_returns_false_for_unmapped_method_without_fallback(
        self,
        mock_has_permission,
    ):
        class TestPermission(ScopedPermission):
            permission_map = {
                "POST": "assets.create",
            }

        user = self.make_user()
        permission = TestPermission()
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_not_called()

    @patch("access.permissions.base.AccessService.has_permission")
    def test_has_permission_supports_multiple_mapped_permissions(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        class TestPermission(ScopedPermission):
            permission_map = {
                "PATCH": [
                    "assets.update",
                    "assets.change_status",
                ],
            }

        user = self.make_user()
        permission = TestPermission()
        request = self.make_request(
            "PATCH",
            user=user,
        )
        view = self.make_view()

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        self.assertEqual(
            mock_has_permission.call_args_list,
            [
                ((user, "assets.update"),),
                ((user, "assets.change_status"),),
            ],
        )

    # ------------------------------------------------------------------
    # view.action mapping
    # ------------------------------------------------------------------

    def test_get_required_permissions_returns_single_permission_from_action_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "list": "assets.view",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view(
            action="list",
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
            ],
        )


    def test_get_required_permissions_returns_multiple_permissions_from_action_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "approve": [
                    "returns.view",
                    "returns.process",
                ],
            }

        permission = TestPermission()
        request = self.make_request("POST")
        view = self.make_view(
            action="approve",
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "returns.view",
                "returns.process",
            ],
        )


    def test_action_map_takes_precedence_over_request_method_map(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "GET": "assets.view",
                "list": "assignments.view",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view(
            action="list",
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assignments.view",
            ],
        )


    def test_falls_back_to_request_method_when_action_is_not_mapped(self):
        class TestPermission(ScopedPermission):
            permission_map = {
                "GET": "assets.view",
                "list": "assignments.view",
            }

        permission = TestPermission()
        request = self.make_request("GET")
        view = self.make_view(
            action="unmapped_action",
        )

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "assets.view",
            ],
        )


    @patch("access.permissions.base.AccessService.has_permission")
    def test_has_permission_uses_action_mapped_permission(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        class TestPermission(ScopedPermission):
            permission_map = {
                "GET": "assets.view",
                "list": "assignments.view",
            }

        user = self.make_user()
        permission = TestPermission()
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view(
            action="list",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_called_once_with(
            user,
            "assignments.view",
        )


    @patch("access.permissions.base.AccessService.has_permission")
    def test_has_permission_supports_multiple_action_mapped_permissions(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        class TestPermission(ScopedPermission):
            permission_map = {
                "approve": [
                    "returns.view",
                    "returns.process",
                ],
            }

        user = self.make_user()
        permission = TestPermission()
        request = self.make_request(
            "POST",
            user=user,
        )
        view = self.make_view(
            action="approve",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        self.assertEqual(
            mock_has_permission.call_args_list,
            [
                call(user, "returns.view"),
                call(user, "returns.process"),
            ],
        )