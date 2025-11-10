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
    API-level enforcement for DepartmentPermission:
      - Uses method_role_map for DEPARTMENT_VIEWER, DEPARTMENT_ADMIN, SITE_ADMIN
      - Scope enforcement at department level
    """

    def setUp(self):
        self.client = APIClient()

        # Departments
        self.dept = DepartmentFactory(name="Chemistry")
        self.other_dept = DepartmentFactory(name="Mathematics")

        # Users
        self.viewer = UserFactory()
        self.dep_admin = UserFactory()
        self.site_admin = AdminUserFactory()

        # Roles
        self.viewer_role = RoleAssignment.objects.create(user=self.viewer, role="DEPARTMENT_VIEWER", department=self.dept)
        self.viewer.active_role = self.viewer_role
        self.viewer.save()

        self.dep_admin_role = RoleAssignment.objects.create(user=self.dep_admin, role="DEPARTMENT_ADMIN", department=self.dept)
        self.dep_admin.active_role = self.dep_admin_role
        self.dep_admin.save()

        self.site_admin_role = RoleAssignment.objects.create(user=self.site_admin, role="SITE_ADMIN")
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

        # URLs
        self.list_url = reverse("departments")  # list/create
        self.detail_url = reverse("department-detail", args=[self.dept.public_id])
        self.other_detail_url = reverse("department-detail", args=[self.other_dept.public_id])

    # --- DEPARTMENT_VIEWER ---
    def test_department_viewer_can_get(self):
        """DEPARTMENT_VIEWER can view their assigned department"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)

    def test_department_viewer_cannot_modify(self):
        """DEPARTMENT_VIEWER cannot modify (POST/PUT/PATCH/DELETE)"""
        self.client.force_authenticate(user=self.viewer)

        post_response = self.client.post(self.list_url, {"name": "New Dept"})
        self.assertIn(post_response.status_code, [403, 405])

        put_response = self.client.put(self.detail_url, {"name": "Updated Dept"})
        self.assertEqual(put_response.status_code, 403)

        patch_response = self.client.patch(self.detail_url, {"name": "Patched Dept"})
        self.assertEqual(patch_response.status_code, 403)

        delete_response = self.client.delete(self.detail_url)
        self.assertEqual(delete_response.status_code, 403)

    # --- DEPARTMENT_ADMIN ---
    def test_department_admin_can_manage_own_department(self):
        """DEPARTMENT_ADMIN can PUT/PATCH their department"""
        self.client.force_authenticate(user=self.dep_admin)

        # GET
        get_response = self.client.get(self.detail_url)
        self.assertIn(get_response.status_code, [200, 204])

        # PUT
        put_response = self.client.put(self.detail_url, {"name": "Updated Chemistry"})
        self.assertIn(put_response.status_code, [200, 204])

        # PATCH
        patch_response = self.client.patch(self.detail_url, {"name": "Patched Chemistry"})
        self.assertIn(patch_response.status_code, [200, 204])

        # DELETE (restricted to SITE_ADMIN)
        delete_response = self.client.delete(self.detail_url)
        self.assertEqual(delete_response.status_code, 403)

    def test_department_admin_cannot_manage_other_department(self):
        """DEPARTMENT_ADMIN cannot modify other departments"""
        self.client.force_authenticate(user=self.dep_admin)

        # GET other dept
        get_response = self.client.get(self.other_detail_url)
        self.assertEqual(get_response.status_code, 403)

        # PUT other dept
        put_response = self.client.put(self.other_detail_url, {"name": "Invalid Update"})
        self.assertEqual(put_response.status_code, 403)

        # PATCH other dept
        patch_response = self.client.patch(self.other_detail_url, {"name": "Invalid Patch"})
        self.assertEqual(patch_response.status_code, 403)

    # --- SITE_ADMIN ---
    def test_site_admin_can_manage_all_departments(self):
        """SITE_ADMIN can fully manage all departments"""
        self.client.force_authenticate(user=self.site_admin)

        get_response = self.client.get(self.detail_url)
        self.assertIn(get_response.status_code, [200, 204])

        post_response = self.client.post(self.list_url, {"name": "New Dept"})
        self.assertIn(post_response.status_code, [200, 201, 204])

        put_response = self.client.put(self.detail_url, {"name": "Updated Dept"})
        self.assertIn(put_response.status_code, [200, 204])

        patch_response = self.client.patch(self.detail_url, {"name": "Patched Dept"})
        self.assertIn(patch_response.status_code, [200, 204])

        delete_response = self.client.delete(self.detail_url)
        self.assertIn(delete_response.status_code, [200, 204])
