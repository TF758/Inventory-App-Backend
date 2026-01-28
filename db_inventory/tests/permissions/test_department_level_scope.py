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

    @classmethod
    def setUpTestData(cls):
        # Departments
        cls.dept1 = DepartmentFactory(name="Physics")
        cls.dept2 = DepartmentFactory(name="Biology")

        # Users
        cls.user = UserFactory()
        cls.site_admin = AdminUserFactory()

        # Site admin role
        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )
        cls.site_admin.active_role = cls.site_admin_role
        cls.site_admin.save()

    def setUp(self):
        self.client = APIClient()

    def test_department_admin_can_access_own_department(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "DEPARTMENT_VIEWER", department=self.dept1))
        self.assertTrue(is_in_scope(role, department=self.dept1))

    def test_department_admin_cannot_access_other_department(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "DEPARTMENT_VIEWER", department=self.dept2))
        self.assertFalse(is_in_scope(role, department=self.dept2))

    def test_site_admin_bypass_department_scope(self):
        self.assertTrue(check_permission(self.site_admin, "DEPARTMENT_ADMIN", department=self.dept1))
        self.assertTrue(check_permission(self.site_admin, "DEPARTMENT_ADMIN", department=self.dept2))
        self.assertTrue(is_in_scope(self.site_admin_role, department=self.dept1))
        self.assertTrue(is_in_scope(self.site_admin_role, department=self.dept2))

    def test_missing_role_cannot_access_department(self):
        self.assertFalse(check_permission(self.user, "DEPARTMENT_VIEWER", department=self.dept1))

    def test_ensure_permission_raises_for_out_of_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept1,
        )
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
    """

    @classmethod
    def setUpTestData(cls):
        cls.dept = DepartmentFactory(
            name="Chemistry",
            description="Initial description",
            img_link="http://example.com/image.png",
        )
        cls.other_dept = DepartmentFactory(name="Mathematics")

        cls.viewer = UserFactory()
        cls.dep_admin = UserFactory()
        cls.site_admin = AdminUserFactory()

        cls.viewer.active_role = RoleAssignment.objects.create(
            user=cls.viewer,
            role="DEPARTMENT_VIEWER",
            department=cls.dept,
        )
        cls.dep_admin.active_role = RoleAssignment.objects.create(
            user=cls.dep_admin,
            role="DEPARTMENT_ADMIN",
            department=cls.dept,
        )
        cls.site_admin.active_role = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )

        for u in (cls.viewer, cls.dep_admin, cls.site_admin):
            u.save()

        cls.list_url = reverse("departments")
        cls.detail_url = reverse("department-detail", args=[cls.dept.public_id])
        cls.other_detail_url = reverse(
            "department-detail",
            args=[cls.other_dept.public_id],
        )

    def setUp(self):
        self.client = APIClient()

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
        self.assertEqual( self.client.patch(self.detail_url, {"description": "X"}).status_code, 403, )
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)

    # ---------------- DEPARTMENT ADMIN ----------------

    def test_department_admin_can_update_description_and_image(self):
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
        self.client.force_authenticate(self.dep_admin)

        response = self.client.patch(
            self.detail_url,
            {"name": "Illegal Rename"},
        )

        self.assertEqual(response.status_code, 403)

    def test_department_admin_cannot_delete_department(self):
        self.client.force_authenticate(self.dep_admin)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)

    def test_department_admin_cannot_access_other_department(self):
        self.client.force_authenticate(self.dep_admin)
        self.assertEqual( self.client.get(self.other_detail_url).status_code, 403, )

    # ---------------- SITE ADMIN ----------------

    def test_site_admin_can_fully_manage_departments(self):
        self.client.force_authenticate(self.site_admin)

        self.assertIn(
            self.client.post(self.list_url, {"name": "New Dept"}).status_code,
            [200, 201, 204],
        )

        self.assertIn( self.client.patch(self.detail_url, {"name": "Renamed"}).status_code, [200, 204], )

        self.assertIn( self.client.patch(self.detail_url, {"description": "Updated"}).status_code, [200, 204], )

        self.assertIn( self.client.delete(self.detail_url).status_code, [200, 204], )