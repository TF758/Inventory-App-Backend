# authorization/tests/test_permission_services.py

from django.test import TestCase

from authorization.services import (
role_has_permission,
user_has_permission,
)

from authorization.tests.utils import (
PermissionTestFixture,
)

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

