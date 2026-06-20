
from django.test import TestCase
from authorization.models import Permission, Role, RolePermission
from authorization.tests.utils import PermissionTestFixture
from authorization.models import Role
from authorization.helpers import invalidate_role_permission_cache, role_has_permission
from authorization.services.users import user_has_permission
from users.models import User
from users.models.roles import RoleAssignment

class TestPermissionServices(TestCase):

    @classmethod
    def setUpTestData(cls):

        fixture = PermissionTestFixture.build()

        cls.department = fixture["department"]

        cls.viewer = fixture["viewer"]
        cls.admin = fixture["admin"]
        cls.site_admin = fixture["site_admin"]

        cls.viewer_role = fixture["viewer_role"]
        cls.admin_role = fixture["admin_role"]

    # =====================================================
    # role_has_permission
    # =====================================================

    def test_role_has_assigned_permission(self):
        self.assertTrue(
            role_has_permission(
                self.viewer_role,
                "test.view",
            )
        )

    def test_role_lacks_unassigned_permission(self):
        self.assertFalse(
            role_has_permission(
                self.viewer_role,
                "test.edit",
            )
        )

    # =====================================================
    # user_has_permission
    # =====================================================

    def test_user_has_permission_from_active_role(self):
        self.assertTrue(
            user_has_permission(
                self.viewer,
                "test.view",
            )
        )

    def test_user_lacks_permission_from_active_role(self):
        self.assertFalse(
            user_has_permission(
                self.viewer,
                "test.edit",
            )
        )

    def test_admin_has_edit_permission(self):
        self.assertTrue(
            user_has_permission(
                self.admin,
                "test.edit",
            )
        )

    def test_admin_has_delete_permission(self):
        self.assertTrue(
            user_has_permission(
                self.admin,
                "test.delete",
            )
        )

    def test_user_without_active_role_denied(self):

        user = User.objects.create(
            email="no-role@test.com",
        )

        self.assertFalse(
            user_has_permission(
                user,
                "test.view",
            )
        )

    def test_unknown_permission_returns_false(self):
        self.assertFalse(
            user_has_permission(
                self.viewer,
                "does.not.exist",
            )
        )

    def test_site_admin_bypass(self):
        self.assertTrue(
            user_has_permission(
                self.site_admin,
                "totally.fake.permission",
            )
        )

    # =====================================================
    # Active role selection
    # =====================================================

    def test_uses_active_role_only(self):

        user = User.objects.create(
            email="switch@test.com",
        )

        viewer_assignment = RoleAssignment.objects.create(
            user=user,
            role="DEPARTMENT_VIEWER",
            role_ref=self.viewer_role,
            department=self.department,
        )

        admin_assignment = RoleAssignment.objects.create(
            user=user,
            role="DEPARTMENT_ADMIN",
            role_ref=self.admin_role,
            department=self.department,
        )

        user.active_role = viewer_assignment
        user.save(update_fields=["active_role"])

        self.assertFalse(
            user_has_permission(
                user,
                "test.delete",
            )
        )

        user.active_role = admin_assignment
        user.save(update_fields=["active_role"])

        self.assertTrue(
            user_has_permission(
                user,
                "test.delete",
            )
        )

    def test_role_with_no_permissions_returns_false(self):


        empty_role = Role.objects.create(
            code="EMPTY_ROLE",
            name="Empty Role",
            scope_type="DEPARTMENT",
            level=1,
        )

        self.assertFalse(
            role_has_permission(
                empty_role,
                "test.view",
            )
        )

    def test_active_role_without_role_ref_returns_false(self):

        user = User.objects.create(
            email="legacy@test.com",
        )

        assignment = RoleAssignment.objects.create(
            user=user,
            role="DEPARTMENT_ADMIN",
            department=self.department,
            role_ref=None,
        )

        user.active_role = assignment
        user.save(update_fields=["active_role"])

        self.assertFalse(
            user_has_permission(
                user,
                "test.view",
            )
        )

    def test_permission_cache_can_be_invalidated(self):

        permission = Permission.objects.create(
            code="test.cached",
            name="Cached Permission",
            module="test",
        )

        self.assertFalse(
            role_has_permission(
                self.viewer_role,
                "test.cached",
            )
        )

        RolePermission.objects.create(
            role=self.viewer_role,
            permission=permission,
        )

        # Cached result should still be stale
        self.assertFalse(
            role_has_permission(
                self.viewer_role,
                "test.cached",
            )
        )

        invalidate_role_permission_cache()

        self.assertTrue(
            role_has_permission(
                self.viewer_role,
                "test.cached",
            )
        )