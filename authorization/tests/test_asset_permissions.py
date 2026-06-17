# authorization/tests/test_asset_permission.py

from types import SimpleNamespace

from django.test import TestCase

from authorization.models import (
Permission,
Role,
RolePermission,
)

from authorization.tests.utils import (
PermissionTestFixture,
)


from authorization.permissions.assets import AssetPermission
from users.models import User
from users.models.roles import RoleAssignment

class TestAssetPermission(TestCase):


    @classmethod
    def setUpTestData(cls):

        fixture = PermissionTestFixture.build()

        cls.department = fixture["department"]

        cls.viewer = fixture["viewer"]
        cls.admin = fixture["admin"]

        cls.viewer_role = fixture["viewer_role"]
        cls.admin_role = fixture["admin_role"]

        # Replace generic permissions with asset permissions

        Permission.objects.all().delete()
        RolePermission.objects.all().delete()

        cls.assets_view = Permission.objects.create(
            code="assets.view",
            name="View Assets",
            module="assets",
        )

        cls.assets_create = Permission.objects.create(
            code="assets.create",
            name="Create Assets",
            module="assets",
        )

        cls.assets_update = Permission.objects.create(
            code="assets.update",
            name="Update Assets",
            module="assets",
        )

        cls.assets_delete = Permission.objects.create(
            code="assets.delete",
            name="Delete Assets",
            module="assets",
        )

        RolePermission.objects.bulk_create([
            RolePermission(
                role=cls.viewer_role,
                permission=cls.assets_view,
            ),

            RolePermission(
                role=cls.admin_role,
                permission=cls.assets_view,
            ),
            RolePermission(
                role=cls.admin_role,
                permission=cls.assets_create,
            ),
            RolePermission(
                role=cls.admin_role,
                permission=cls.assets_update,
            ),
            RolePermission(
                role=cls.admin_role,
                permission=cls.assets_delete,
            ),
        ])

        cls.permission = AssetPermission()

    def make_request(self, method, user):

        return SimpleNamespace(
            method=method,
            user=user,
        )

    # =====================================================
    # GET -> assets.view
    # =====================================================

    def test_get_allows_view_permission(self):

        request = self.make_request(
            "GET",
            self.viewer,
        )

        self.assertTrue(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    # =====================================================
    # POST -> assets.create
    # =====================================================

    def test_post_denies_user_without_create_permission(self):

        request = self.make_request(
            "POST",
            self.viewer,
        )

        self.assertFalse(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    def test_post_allows_user_with_create_permission(self):

        request = self.make_request(
            "POST",
            self.admin,
        )

        self.assertTrue(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    # =====================================================
    # PUT -> assets.update
    # =====================================================

    def test_put_requires_update_permission(self):

        request = self.make_request(
            "PUT",
            self.admin,
        )

        self.assertTrue(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    # =====================================================
    # PATCH -> assets.update
    # =====================================================

    def test_patch_requires_update_permission(self):

        request = self.make_request(
            "PATCH",
            self.admin,
        )

        self.assertTrue(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    # =====================================================
    # DELETE -> assets.delete
    # =====================================================

    def test_delete_requires_delete_permission(self):

        request = self.make_request(
            "DELETE",
            self.admin,
        )

        self.assertTrue(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    def test_delete_denied_without_delete_permission(self):

        request = self.make_request(
            "DELETE",
            self.viewer,
        )

        self.assertFalse(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    # =====================================================
    # Unsupported methods
    # =====================================================

    def test_unknown_method_denied(self):

        request = self.make_request(
            "OPTIONS",
            self.admin,
        )

        self.assertFalse(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

