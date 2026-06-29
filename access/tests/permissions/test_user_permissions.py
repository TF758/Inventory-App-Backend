# access/tests/permissions/test_user_permissions.py

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.permissions import SAFE_METHODS

from access.permissions.users import (
    UserPermission,
    UserProfilePermission,
)


class UserPermissionTests(SimpleTestCase):
    """
    Unit tests for UserPermission.

    UserPermission is identity/self-service based:

        - authenticated users pass has_permission
        - users may always access themselves
        - safe-method access to other users requires users.view
        - write access to other users is denied
        - self update is allowed
    """

    def make_user(
        self,
        id=1,
        *,
        is_authenticated=True,
        active_role=None,
    ):
        return SimpleNamespace(
            id=id,
            is_authenticated=is_authenticated,
            active_role=active_role,
        )

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

    def make_view(self):
        return SimpleNamespace()

    # ------------------------------------------------------------------
    # has_permission
    # ------------------------------------------------------------------

    def test_has_permission_returns_false_without_user(self):
        permission = UserPermission()
        request = self.make_request(
            user=None,
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    def test_has_permission_returns_false_for_unauthenticated_user(self):
        permission = UserPermission()
        request = self.make_request(
            user=self.make_user(
                is_authenticated=False,
            ),
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    def test_has_permission_returns_true_for_authenticated_user(self):
        permission = UserPermission()
        request = self.make_request(
            user=self.make_user(
                is_authenticated=True,
            ),
        )

        self.assertTrue(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    # ------------------------------------------------------------------
    # Self access
    # ------------------------------------------------------------------

    @patch("access.permissions.users.AccessService.has_permission")
    def test_has_object_permission_allows_self_access_without_access_service(
        self,
        mock_has_permission,
    ):
        permission = UserPermission()
        user = self.make_user(id=1)
        request = self.make_request(
            "GET",
            user=user,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                user,
            )
        )

        mock_has_permission.assert_not_called()

    # ------------------------------------------------------------------
    # Directory read access
    # ------------------------------------------------------------------

    @patch("access.permissions.users.AccessService.has_permission")
    def test_safe_method_other_user_requires_users_view_permission(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        permission = UserPermission()
        user = self.make_user(id=1)
        other_user = self.make_user(id=2)
        request = self.make_request(
            "GET",
            user=user,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_called_once_with(
            user,
            "users.view",
        )

    @patch("access.permissions.users.AccessService.has_permission")
    def test_safe_method_other_user_denied_without_users_view_permission(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        permission = UserPermission()
        user = self.make_user(id=1)
        other_user = self.make_user(id=2)
        request = self.make_request(
            "GET",
            user=user,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_called_once_with(
            user,
            "users.view",
        )

    @patch("access.permissions.users.AccessService.has_permission")
    def test_all_safe_methods_for_other_user_use_users_view_permission(
        self,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True

        permission = UserPermission()
        user = self.make_user(id=1)
        other_user = self.make_user(id=2)

        for method in SAFE_METHODS:
            with self.subTest(method=method):
                mock_has_permission.reset_mock()

                request = self.make_request(
                    method,
                    user=user,
                )

                self.assertTrue(
                    permission.has_object_permission(
                        request,
                        self.make_view(),
                        other_user,
                    )
                )

                mock_has_permission.assert_called_once_with(
                    user,
                    "users.view",
                )

    # ------------------------------------------------------------------
    # Write access
    # ------------------------------------------------------------------

    @patch("access.permissions.users.AccessService.has_permission")
    def test_put_allows_self_update_without_access_service(
        self,
        mock_has_permission,
    ):
        permission = UserPermission()
        user = self.make_user(id=1)
        request = self.make_request(
            "PUT",
            user=user,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                user,
            )
        )

        mock_has_permission.assert_not_called()

    @patch("access.permissions.users.AccessService.has_permission")
    def test_patch_allows_self_update_without_access_service(
        self,
        mock_has_permission,
    ):
        permission = UserPermission()
        user = self.make_user(id=1)
        request = self.make_request(
            "PATCH",
            user=user,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                user,
            )
        )

        mock_has_permission.assert_not_called()

    @patch("access.permissions.users.AccessService.has_permission")
    def test_put_denies_other_user_update(
        self,
        mock_has_permission,
    ):
        permission = UserPermission()
        user = self.make_user(id=1)
        other_user = self.make_user(id=2)
        request = self.make_request(
            "PUT",
            user=user,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_not_called()

    @patch("access.permissions.users.AccessService.has_permission")
    def test_patch_denies_other_user_update(
        self,
        mock_has_permission,
    ):
        permission = UserPermission()
        user = self.make_user(id=1)
        other_user = self.make_user(id=2)
        request = self.make_request(
            "PATCH",
            user=user,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_not_called()

    @patch("access.permissions.users.AccessService.has_permission")
    def test_delete_denies_other_user(
        self,
        mock_has_permission,
    ):
        permission = UserPermission()
        user = self.make_user(id=1)
        other_user = self.make_user(id=2)
        request = self.make_request(
            "DELETE",
            user=user,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_not_called()


class UserProfilePermissionTests(SimpleTestCase):
    """
    Unit tests for UserProfilePermission.

    UserProfilePermission is a scoped profile permission:

        - users may access their own profile
        - other-user access requires an active role
        - other-user access requires users.view
        - other-user access must pass UserScopeService
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
        id=1,
        *,
        is_authenticated=True,
        active_role=None,
    ):
        return SimpleNamespace(
            id=id,
            is_authenticated=is_authenticated,
            active_role=active_role,
        )

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

    def make_view(self):
        return SimpleNamespace()

    # ------------------------------------------------------------------
    # Method map
    # ------------------------------------------------------------------

    def test_method_map_returns_users_view_for_get(self):
        permission = UserProfilePermission()
        request = self.make_request("GET")
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

    # ------------------------------------------------------------------
    # Self access
    # ------------------------------------------------------------------

    @patch.object(UserProfilePermission, "has_permission")
    @patch("access.services.scope.UserScopeService.can_access_user")
    def test_has_object_permission_allows_self_access_without_permission_or_scope(
        self,
        mock_can_access_user,
        mock_has_permission,
    ):
        permission = UserProfilePermission()
        user = self.make_user(id=1)
        request = self.make_request(
            "GET",
            user=user,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                user,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_user.assert_not_called()

    # ------------------------------------------------------------------
    # Other-user access
    # ------------------------------------------------------------------

    @patch.object(UserProfilePermission, "has_permission")
    @patch("access.services.scope.UserScopeService.can_access_user")
    def test_has_object_permission_returns_false_without_active_role_for_other_user(
        self,
        mock_can_access_user,
        mock_has_permission,
    ):
        permission = UserProfilePermission()
        user = self.make_user(
            id=1,
            active_role=None,
        )
        other_user = self.make_user(id=2)
        request = self.make_request(
            "GET",
            user=user,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_not_called()
        mock_can_access_user.assert_not_called()

    @patch.object(UserProfilePermission, "has_permission")
    @patch("access.services.scope.UserScopeService.can_access_user")
    def test_has_object_permission_returns_false_when_base_permission_denied(
        self,
        mock_can_access_user,
        mock_has_permission,
    ):
        mock_has_permission.return_value = False

        permission = UserProfilePermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(
            id=1,
            active_role=active_role,
        )
        other_user = self.make_user(id=2)
        request = self.make_request(
            "GET",
            user=user,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                other_user,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            self.make_view(),
        )
        mock_can_access_user.assert_not_called()

    @patch.object(UserProfilePermission, "has_permission")
    @patch("access.services.scope.UserScopeService.can_access_user")
    def test_has_object_permission_returns_false_when_user_scope_denied(
        self,
        mock_can_access_user,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_user.return_value = False

        permission = UserProfilePermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        user = self.make_user(
            id=1,
            active_role=active_role,
        )
        other_user = self.make_user(id=2)
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                other_user,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_user.assert_called_once_with(
            active_role,
            other_user,
        )

    @patch.object(UserProfilePermission, "has_permission")
    @patch("access.services.scope.UserScopeService.can_access_user")
    def test_has_object_permission_returns_true_when_permission_and_scope_allowed(
        self,
        mock_can_access_user,
        mock_has_permission,
    ):
        mock_has_permission.return_value = True
        mock_can_access_user.return_value = True

        permission = UserProfilePermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        user = self.make_user(
            id=1,
            active_role=active_role,
        )
        other_user = self.make_user(id=2)
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                other_user,
            )
        )

        mock_has_permission.assert_called_once_with(
            request,
            view,
        )
        mock_can_access_user.assert_called_once_with(
            active_role,
            other_user,
        )