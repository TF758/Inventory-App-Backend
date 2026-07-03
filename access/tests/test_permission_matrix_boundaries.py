from django.test import TestCase

from rest_framework.exceptions import ValidationError

from access.models import Permission, RolePermission
from access.serialziers import PermissionMatrixUpdateSerializer
from access.services.permissions import PermissionMatrixService


class PermissionMatrixBoundaryTests(TestCase):
    """
    Tests that role-permission compatibility boundaries are enforced
    at the matrix serializer and matrix service layers.

    The pure policy tests already prove whether a role type may ever
    receive a permission code.

    These tests prove the matrix cannot save incompatible grants.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_permission(
        self,
        code,
        *,
        domain=None,
        configurable=True,
        sort_order=1,
    ):
        return Permission.objects.create(
            domain=domain or code.split(".")[0],
            code=code,
            name=code.replace(
                ".",
                " ",
            ).title(),
            scope_type="SCOPED",
            description="Test permission.",
            sort_order=sort_order,
            is_configurable=configurable,
        )

    def make_payload(
        self,
        permission_code,
        roles,
        *,
        domain=None,
    ):
        return {
            "domains": [
                {
                    "code": domain or permission_code.split(".")[0],
                    "permissions": [
                        {
                            "code": permission_code,
                            "roles": roles,
                        }
                    ],
                }
            ],
        }

    def enabled_role(
        self,
        role,
    ):
        return {
            "role": role,
            "enabled": True,
        }

    def disabled_role(
        self,
        role,
    ):
        return {
            "role": role,
            "enabled": False,
        }

    def assert_serializer_error_contains(
        self,
        serializer,
        expected_text,
    ):
        self.assertIn(
            expected_text,
            str(serializer.errors),
        )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setUp(self):
        self.assets_create = self.make_permission(
            "assets.create",
            domain="assets",
            sort_order=100,
        )

        self.assets_view = self.make_permission(
            "assets.view",
            domain="assets",
            sort_order=101,
        )

        self.rooms_view = self.make_permission(
            "rooms.view",
            domain="rooms",
            sort_order=200,
        )

        self.departments_view = self.make_permission(
            "departments.view",
            domain="departments",
            sort_order=300,
        )

    # ------------------------------------------------------------------
    # Serializer boundary enforcement
    # ------------------------------------------------------------------

    def test_serializer_rejects_invalid_enabled_grant(self):
        payload = self.make_payload(
            "assets.create",
            [
                self.enabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        serializer = PermissionMatrixUpdateSerializer(
            data=payload,
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assert_serializer_error_contains(
            serializer,
            "ROOM_VIEWER cannot be granted assets.create.",
        )

    def test_serializer_allows_invalid_grant_when_disabled(self):
        payload = self.make_payload(
            "assets.create",
            [
                self.disabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        serializer = PermissionMatrixUpdateSerializer(
            data=payload,
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_serializer_allows_valid_room_viewer_view_grant(self):
        payload = self.make_payload(
            "rooms.view",
            [
                self.enabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        serializer = PermissionMatrixUpdateSerializer(
            data=payload,
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_serializer_rejects_location_viewer_department_view_grant(self):
        payload = self.make_payload(
            "departments.view",
            [
                self.enabled_role(
                    "LOCATION_VIEWER",
                )
            ],
        )

        serializer = PermissionMatrixUpdateSerializer(
            data=payload,
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assert_serializer_error_contains(
            serializer,
            "LOCATION_VIEWER cannot be granted departments.view.",
        )

    def test_serializer_allows_department_viewer_department_view_grant(self):
        payload = self.make_payload(
            "departments.view",
            [
                self.enabled_role(
                    "DEPARTMENT_VIEWER",
                )
            ],
        )

        serializer = PermissionMatrixUpdateSerializer(
            data=payload,
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_serializer_rejects_site_admin_role_toggle(self):
        payload = self.make_payload(
            "assets.view",
            [
                self.enabled_role(
                    "SITE_ADMIN",
                )
            ],
        )

        serializer = PermissionMatrixUpdateSerializer(
            data=payload,
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assert_serializer_error_contains(
            serializer,
            "SITE_ADMIN",
        )

    # ------------------------------------------------------------------
    # Service boundary enforcement
    # ------------------------------------------------------------------

    def test_service_rejects_invalid_enabled_grant(self):
        payload = self.make_payload(
            "assets.create",
            [
                self.enabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        with self.assertRaises(ValidationError) as exc:
            PermissionMatrixService.update_matrix(
                payload,
            )

        self.assertEqual(
            str(exc.exception.detail["detail"]),
            "ROOM_VIEWER cannot be granted assets.create.",
        )

        self.assertEqual(
            exc.exception.detail["invalid_grants"][0]["role"],
            "ROOM_VIEWER",
        )
        self.assertEqual(
            exc.exception.detail["invalid_grants"][0]["permission"],
            "assets.create",
        )

        self.assertFalse(
            RolePermission.objects.filter(
                role="ROOM_VIEWER",
                permission=self.assets_create,
            ).exists()
        )

    def test_service_allows_invalid_grant_when_disabled(self):
        payload = self.make_payload(
            "assets.create",
            [
                self.disabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        matrix = PermissionMatrixService.update_matrix(
            payload,
        )

        self.assertFalse(
            RolePermission.objects.filter(
                role="ROOM_VIEWER",
                permission=self.assets_create,
            ).exists()
        )

        self.assertEqual(
            matrix["meta"]["changes"]["created"],
            0,
        )
        self.assertEqual(
            matrix["meta"]["changes"]["deleted"],
            0,
        )
        self.assertFalse(
            matrix["meta"]["changes"]["changed"],
        )

    def test_service_creates_valid_grant(self):
        payload = self.make_payload(
            "rooms.view",
            [
                self.enabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        matrix = PermissionMatrixService.update_matrix(
            payload,
        )

        self.assertTrue(
            RolePermission.objects.filter(
                role="ROOM_VIEWER",
                permission=self.rooms_view,
            ).exists()
        )

        self.assertEqual(
            matrix["meta"]["changes"]["created"],
            1,
        )
        self.assertEqual(
            matrix["meta"]["changes"]["deleted"],
            0,
        )
        self.assertTrue(
            matrix["meta"]["changes"]["changed"],
        )

    def test_service_deletes_historical_invalid_grant_when_disabled(self):
        RolePermission.objects.create(
            role="ROOM_VIEWER",
            permission=self.assets_create,
        )

        payload = self.make_payload(
            "assets.create",
            [
                self.disabled_role(
                    "ROOM_VIEWER",
                )
            ],
        )

        matrix = PermissionMatrixService.update_matrix(
            payload,
        )

        self.assertFalse(
            RolePermission.objects.filter(
                role="ROOM_VIEWER",
                permission=self.assets_create,
            ).exists()
        )

        self.assertEqual(
            matrix["meta"]["changes"]["created"],
            0,
        )
        self.assertEqual(
            matrix["meta"]["changes"]["deleted"],
            1,
        )
        self.assertTrue(
            matrix["meta"]["changes"]["changed"],
        )

    def test_service_allows_department_viewer_department_view_grant(self):
        payload = self.make_payload(
            "departments.view",
            [
                self.enabled_role(
                    "DEPARTMENT_VIEWER",
                )
            ],
        )

        matrix = PermissionMatrixService.update_matrix(
            payload,
        )

        self.assertTrue(
            RolePermission.objects.filter(
                role="DEPARTMENT_VIEWER",
                permission=self.departments_view,
            ).exists()
        )

        self.assertEqual(
            matrix["meta"]["changes"]["created"],
            1,
        )