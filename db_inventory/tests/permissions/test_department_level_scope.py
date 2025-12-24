from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework.exceptions import PermissionDenied
from db_inventory.factories import (
    UserFactory,
    DepartmentFactory,
    LocationFactory,
    AdminUserFactory,
)
from db_inventory.models import RoleAssignment
from db_inventory.permissions.helpers import is_in_scope, check_permission, ensure_permission


# -------------------------------
# UNIT LEVEL TESTS
# -------------------------------

class DepartmentAdminScopeTests(APITestCase):
    """
    Unit-level tests for Department permission & scope behavior.
    Covers: DEPARTMENT_ADMIN, DEPARTMENT_VIEWER, SITE_ADMIN.
    """

    def setUp(self):
        self.client = APIClient()
        self.dept1 = DepartmentFactory(name="Physics")
        self.dept2 = DepartmentFactory(name="Biology")

        self.user = UserFactory()
        self.site_admin = AdminUserFactory()

        # Assign site admin role
        self.site_admin_role = RoleAssignment.objects.create(user=self.site_admin, role="SITE_ADMIN")
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

    def test_department_admin_can_access_own_department(self):
        """DEPARTMENT_ADMIN can access their own department"""
        role = RoleAssignment.objects.create(user=self.user, role="DEPARTMENT_ADMIN", department=self.dept1)
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "DEPARTMENT_VIEWER", department=self.dept1))
        self.assertTrue(is_in_scope(role, department=self.dept1))

    def test_department_admin_cannot_access_other_department(self):
        """DEPARTMENT_ADMIN cannot access other departments"""
        role = RoleAssignment.objects.create(user=self.user, role="DEPARTMENT_ADMIN", department=self.dept1)
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "DEPARTMENT_VIEWER", department=self.dept2))
        self.assertFalse(is_in_scope(role, department=self.dept2))

    def test_site_admin_bypass_department_scope(self):
        """SITE_ADMIN can access all departments"""
        self.assertTrue(check_permission(self.site_admin, "DEPARTMENT_ADMIN", department=self.dept1))
        self.assertTrue(check_permission(self.site_admin, "DEPARTMENT_ADMIN", department=self.dept2))
        self.assertTrue(is_in_scope(self.site_admin_role, department=self.dept1))
        self.assertTrue(is_in_scope(self.site_admin_role, department=self.dept2))

    def test_missing_role_cannot_access_department(self):
        """User with no active role is denied access"""
        self.assertFalse(check_permission(self.user, "DEPARTMENT_VIEWER", department=self.dept1))

    def test_ensure_permission_raises_for_out_of_scope(self):
        """ensure_permission should raise PermissionDenied if department out of scope"""
        role = RoleAssignment.objects.create(user=self.user, role="DEPARTMENT_ADMIN", department=self.dept1)
        self.user.active_role = role
        self.user.save()

        with self.assertRaises(PermissionDenied):
            ensure_permission(self.user, "DEPARTMENT_ADMIN", department=self.dept2)


# -------------------------------
# API LEVEL TESTS
# -------------------------------

class DepartmentPermissionAPITests(APITestCase):
    """
    API-level enforcement for DepartmentPermission.
    Enforces:
      - Field-level restrictions (name vs description/image)
      - Scope enforcement
      - Role hierarchy
    """

    def setUp(self):
        self.client = APIClient()

        self.dept = DepartmentFactory(
            name="Chemistry",
            description="Initial description",
            img_link="http://example.com/image.png",
        )
        self.other_dept = DepartmentFactory(name="Mathematics")

        self.viewer = UserFactory()
        self.dep_admin = UserFactory()
        self.site_admin = AdminUserFactory()

        # Roles
        self.viewer.active_role = RoleAssignment.objects.create(
            user=self.viewer, role="DEPARTMENT_VIEWER", department=self.dept
        )
        self.dep_admin.active_role = RoleAssignment.objects.create(
            user=self.dep_admin, role="DEPARTMENT_ADMIN", department=self.dept
        )
        self.site_admin.active_role = RoleAssignment.objects.create(
            user=self.site_admin, role="SITE_ADMIN"
        )

        for u in [self.viewer, self.dep_admin, self.site_admin]:
            u.save()

        self.list_url = reverse("departments")
        self.detail_url = reverse("department-detail", args=[self.dept.public_id])
        self.other_detail_url = reverse("department-detail", args=[self.other_dept.public_id])

    # ---------------- VIEWER ----------------

    def test_department_viewer_can_get(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)

    def test_department_viewer_cannot_modify(self):
        self.client.force_authenticate(self.viewer)

        self.assertIn(
            self.client.post(self.list_url, {"name": "X"}).status_code,
            [403, 405],
        )
        self.assertEqual(self.client.patch(self.detail_url, {"description": "X"}).status_code, 403)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)

    # ---------------- DEPARTMENT ADMIN ----------------

    def test_department_admin_can_update_description_and_image(self):
        """DEPARTMENT_ADMIN can update description and image within scope"""

        self.client.force_authenticate(self.dep_admin)

        response = self.client.patch(
            self.detail_url,
            {
                "description": "Updated description",
                "img_link": "http://example.com/new.png",
            },
        )

        self.assertIn(response.status_code, [200, 204])

    def test_department_admin_cannot_change_name(self):
        """DEPARTMENT_ADMIN cannot change department name"""

        self.client.force_authenticate(self.dep_admin)

        response = self.client.patch(
            self.detail_url,
            {"name": "Illegal Rename"}
        )

        self.assertEqual(response.status_code, 403)

    def test_department_admin_cannot_delete_department(self):
        """DEPARTMENT_ADMIN cannot delete department"""

        self.client.force_authenticate(self.dep_admin)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)

    def test_department_admin_cannot_access_other_department(self):
        self.client.force_authenticate(self.dep_admin)
        self.assertEqual(self.client.get(self.other_detail_url).status_code, 403)

    # ---------------- SITE ADMIN ----------------

    def test_site_admin_can_fully_manage_departments(self):
        """SITE_ADMIN can create, rename, update, and delete departments"""

        self.client.force_authenticate(self.site_admin)

        # POST
        self.assertIn(
            self.client.post(self.list_url, {"name": "New Dept"}).status_code,
            [200, 201, 204],
        )

        # PATCH name
        self.assertIn(
            self.client.patch(self.detail_url, {"name": "Renamed"}).status_code,
            [200, 204],
        )

        # PATCH description
        self.assertIn(
            self.client.patch(self.detail_url, {"description": "Updated"}).status_code,
            [200, 204],
        )

        # DELETE
        self.assertIn(
            self.client.delete(self.detail_url).status_code,
            [200, 204],
        )