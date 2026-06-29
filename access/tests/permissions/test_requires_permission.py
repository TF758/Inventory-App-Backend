# access/tests/test_requires_permission.py

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.permissions.base import RequiresPermission



class RequiresPermissionTests(SimpleTestCase):
    """
    Unit tests for RequiresPermission.

    RequiresPermission answers:

        - Is the request authenticated?
        - Which permission code(s) are required?
        - Does AccessService allow all required permissions?

    These tests intentionally do not test:
        - database-backed RolePermission rows
        - object scope
        - serializers
        - DRF viewsets
        - API routing
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_user(self, *, is_authenticated=True):
        return SimpleNamespace(
            is_authenticated=is_authenticated,
        )

    def make_request(self, user=None):
        return SimpleNamespace(
            user=user,
        )

    def make_view(
        self,
        *,
        required_permission=None,
        required_permissions=None,
    ):
        view = SimpleNamespace()

        if required_permission is not None:
            view.required_permission = required_permission

        if required_permissions is not None:
            view.required_permissions = required_permissions

        return view

    # ------------------------------------------------------------------
    # get_required_permissions
    # ------------------------------------------------------------------

    def test_get_required_permissions_returns_view_required_permissions(self):
        permission = RequiresPermission()
        request = self.make_request(
            user=self.make_user(),
        )
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

    def test_get_required_permissions_returns_view_required_permission_as_list(self):
        permission = RequiresPermission()
        request = self.make_request(
            user=self.make_user(),
        )
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

    def test_get_required_permissions_prefers_required_permissions_over_required_permission(self):
        permission = RequiresPermission()
        request = self.make_request(
            user=self.make_user(),
        )
        view = self.make_view(
            required_permission="assets.view",
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

    def test_get_required_permissions_uses_class_required_permissions_fallback(self):
        class TestPermission(RequiresPermission):
            required_permissions = [
                "users.view",
                "users.update",
            ]

        permission = TestPermission()
        request = self.make_request(
            user=self.make_user(),
        )
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "users.view",
                "users.update",
            ],
        )

    def test_get_required_permissions_uses_class_required_permission_fallback(self):
        class TestPermission(RequiresPermission):
            required_permission = "users.view"

        permission = TestPermission()
        request = self.make_request(
            user=self.make_user(),
        )
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [
                "users.view",
            ],
        )

    def test_get_required_permissions_returns_empty_list_when_none_configured(self):
        permission = RequiresPermission()
        request = self.make_request(
            user=self.make_user(),
        )
        view = self.make_view()

        self.assertEqual(
            permission.get_required_permissions(
                request,
                view,
            ),
            [],
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_false_without_user(
        self,
        mock_has_permission,
    ):
        permission = RequiresPermission()
        request = self.make_request(
            user=None,
        )
        view = self.make_view(
            required_permission="assets.view",
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_not_called()

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_false_for_unauthenticated_user(
        self,
        mock_has_permission,
    ):
        permission = RequiresPermission()
        request = self.make_request(
            user=self.make_user(
                is_authenticated=False,
            ),
        )
        view = self.make_view(
            required_permission="assets.view",
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_not_called()

    # ------------------------------------------------------------------
    # Missing configuration
    # ------------------------------------------------------------------

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_false_when_no_permission_configured(
        self,
        mock_has_permission,
    ):
        permission = RequiresPermission()
        request = self.make_request(
            user=self.make_user(),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_not_called()

    # ------------------------------------------------------------------
    # Single permission
    # ------------------------------------------------------------------

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_true_when_single_permission_allowed(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        user = self.make_user()
        permission = RequiresPermission()
        request = self.make_request(
            user=user,
        )
        view = self.make_view(
            required_permission="assets.view",
        )

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

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_false_when_single_permission_denied(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        user = self.make_user()
        permission = RequiresPermission()
        request = self.make_request(
            user=user,
        )
        view = self.make_view(
            required_permission="assets.create",
        )

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

    # ------------------------------------------------------------------
    # Multiple permissions
    # ------------------------------------------------------------------

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_true_when_all_permissions_allowed(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        user = self.make_user()
        permission = RequiresPermission()
        request = self.make_request(
            user=user,
        )
        view = self.make_view(
            required_permissions=[
                "assets.view",
                "assets.update",
            ],
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
                ((user, "assets.view"),),
                ((user, "assets.update"),),
            ],
        )

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_returns_false_when_any_permission_is_denied(
        self,
        mock_has_permission,
    ):
        mock_has_permission.side_effect = [
            True,
            False,
        ]

        user = self.make_user()
        permission = RequiresPermission()
        request = self.make_request(
            user=user,
        )
        view = self.make_view(
            required_permissions=[
                "assets.view",
                "assets.update",
            ],
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        self.assertEqual(
            mock_has_permission.call_args_list,
            [
                ((user, "assets.view"),),
                ((user, "assets.update"),),
            ],
        )

    @patch("access.services.access.AccessService.has_permission")
    def test_has_permission_short_circuits_after_first_denied_permission(
        self,
        mock_has_permission,
    ):
        mock_has_permission.side_effect = [
            False,
            True,
        ]

        user = self.make_user()
        permission = RequiresPermission()
        request = self.make_request(
            user=user,
        )
        view = self.make_view(
            required_permissions=[
                "assets.view",
                "assets.update",
            ],
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_has_permission.assert_called_once_with(
            user,
            "assets.view",
        )