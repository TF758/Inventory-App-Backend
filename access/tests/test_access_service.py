from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.services.access import AccessService


class AccessServiceTests(SimpleTestCase):
    """
    Unit tests for AccessService.

    AccessService only answers:

        "Does the user's active role have this permission code?"

    These tests intentionally avoid the database. Database-backed behavior
    for Permission / RolePermission belongs in model or integration tests.
    """

    def make_user(self, role=None):
        active_role = None

        if role:
            active_role = SimpleNamespace(role=role)

        return SimpleNamespace(active_role=active_role)

    # ------------------------------------------------------------------
    # No active role
    # ------------------------------------------------------------------

    @patch("access.services.access.RolePermission.objects.filter")
    def test_returns_false_when_user_has_no_active_role(self, mock_filter):
        user = self.make_user()

        result = AccessService.has_permission(
            user,
            "assets.view",
        )

        self.assertFalse(result)
        mock_filter.assert_not_called()

    @patch("access.services.access.RolePermission.objects.filter")
    def test_returns_false_when_user_has_no_active_role_attribute(self, mock_filter):
        user = SimpleNamespace()

        result = AccessService.has_permission(
            user,
            "assets.view",
        )

        self.assertFalse(result)
        mock_filter.assert_not_called()

    # ------------------------------------------------------------------
    # SITE_ADMIN bypass
    # ------------------------------------------------------------------

    @patch("access.services.access.RolePermission.objects.filter")
    def test_site_admin_bypasses_permission_matrix(self, mock_filter):
        user = self.make_user("SITE_ADMIN")

        result = AccessService.has_permission(
            user,
            "any.permission.code",
        )

        self.assertTrue(result)
        mock_filter.assert_not_called()

    @patch("access.services.access.RolePermission.objects.filter")
    def test_site_admin_does_not_need_permission_row_to_exist(self, mock_filter):
        user = self.make_user("SITE_ADMIN")

        result = AccessService.has_permission(
            user,
            "permissions.that.do.not.exist",
        )

        self.assertTrue(result)
        mock_filter.assert_not_called()

    # ------------------------------------------------------------------
    # Permission lookup
    # ------------------------------------------------------------------

    @patch("access.services.access.RolePermission.objects.filter")
    def test_returns_true_when_active_role_has_permission(self, mock_filter):
        mock_filter.return_value.exists.return_value = True

        user = self.make_user("ROOM_ADMIN")

        result = AccessService.has_permission(
            user,
            "assets.create",
        )

        self.assertTrue(result)

        mock_filter.assert_called_once_with(
            role="ROOM_ADMIN",
            permission__code="assets.create",
        )

    @patch("access.services.access.RolePermission.objects.filter")
    def test_returns_false_when_active_role_lacks_permission(self, mock_filter):
        mock_filter.return_value.exists.return_value = False

        user = self.make_user("ROOM_VIEWER")

        result = AccessService.has_permission(
            user,
            "assets.create",
        )

        self.assertFalse(result)

        mock_filter.assert_called_once_with(
            role="ROOM_VIEWER",
            permission__code="assets.create",
        )

    @patch("access.services.access.RolePermission.objects.filter")
    def test_permission_lookup_uses_exact_permission_code(self, mock_filter):
        mock_filter.return_value.exists.return_value = True

        user = self.make_user("LOCATION_ADMIN")

        result = AccessService.has_permission(
            user,
            "assets.update_status",
        )

        self.assertTrue(result)

        mock_filter.assert_called_once_with(
            role="LOCATION_ADMIN",
            permission__code="assets.update_status",
        )

    @patch("access.services.access.RolePermission.objects.filter")
    def test_permission_lookup_uses_only_active_role(self, mock_filter):
        mock_filter.return_value.exists.return_value = False

        user = self.make_user("ROOM_CLERK")

        result = AccessService.has_permission(
            user,
            "assets.delete",
        )

        self.assertFalse(result)

        mock_filter.assert_called_once_with(
            role="ROOM_CLERK",
            permission__code="assets.delete",
        )