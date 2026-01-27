from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from db_inventory.models import User, RoleAssignment, Department
from db_inventory.factories import AdminUserFactory, DepartmentFactory, LocationFactory, UserFactory, RoomFactory
from rest_framework.test import force_authenticate
from rest_framework.test import APIClient

class UserPermissionSiteAdminTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.site_admin = AdminUserFactory()
        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
            assigned_by=cls.site_admin,
        )
        cls.site_admin.active_role = cls.site_admin_role
        cls.site_admin.save()

        cls.target_user = UserFactory()

        cls.list_url = reverse("users")
        cls.detail_url = reverse(
            "user-detail", kwargs={"public_id": cls.target_user.public_id}
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.site_admin)

    def test_site_admin_can_view_users(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_200_OK)

    def test_site_admin_cannot_create_users_here(self):
        self.assertEqual(
            self.client.post(self.list_url, {}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_site_admin_cannot_delete_users_here(self):
        self.assertEqual(
            self.client.delete(self.detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

class DepartmentAdminUserPermissionTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()

        cls.admin = UserFactory()
        cls.admin_role = RoleAssignment.objects.create(
            user=cls.admin,
            role="DEPARTMENT_ADMIN",
            department=cls.department,
            assigned_by=cls.admin,
        )
        cls.admin.active_role = cls.admin_role
        cls.admin.save()

        cls.user = UserFactory()

        cls.list_url = reverse("users")
        cls.detail_url = reverse(
            "user-detail", kwargs={"public_id": cls.user.public_id}
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_department_admin_can_view_users(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_200_OK)

    def test_department_admin_cannot_modify_users_here(self):
        self.assertEqual(
            self.client.post(self.list_url, {}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED, )
        self.assertEqual(
            self.client.patch(self.detail_url, {"fname": "X"}).status_code, status.HTTP_403_FORBIDDEN, )
        self.assertEqual(
            self.client.delete(self.detail_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED, )

class LocationAdminUserPermissionTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)

        cls.admin = UserFactory()
        cls.admin_role = RoleAssignment.objects.create(
            user=cls.admin,
            role="LOCATION_ADMIN",
            location=cls.location,
        )
        cls.admin.active_role = cls.admin_role
        cls.admin.save()

        cls.target_user = UserFactory()

        cls.list_url = reverse("users")
        cls.detail_url = reverse(
            "user-detail", kwargs={"public_id": cls.target_user.public_id}
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_location_admin_can_view_users(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_location_admin_cannot_modify_users(self):
        self.assertEqual(
            self.client.patch(self.detail_url, {"fname": "X"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

class ViewerUserPermissionTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()

        cls.viewer = UserFactory()
        cls.viewer_role = RoleAssignment.objects.create(
            user=cls.viewer,
            role="DEPARTMENT_VIEWER",
            department=cls.department,
        )
        cls.viewer.active_role = cls.viewer_role
        cls.viewer.save()

        cls.other_user = UserFactory()

        cls.list_url = reverse("users")
        cls.detail_url = reverse(
            "user-detail", kwargs={"public_id": cls.other_user.public_id}
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.viewer)

    def test_viewer_can_view_users(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_viewer_cannot_modify_users(self):
        self.assertEqual(
            self.client.patch(self.detail_url, {"fname": "X"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

class ViewerUserPermissionTest(APITestCase):

    def setUp(self):
        dept = DepartmentFactory()

        self.viewer = UserFactory()
        role = RoleAssignment.objects.create(
            user=self.viewer,
            role="DEPARTMENT_VIEWER",
            department=dept,
        )
        self.viewer.active_role = role
        self.viewer.save()

        self.other_user = UserFactory()

        self.client.force_authenticate(self.viewer)

        self.list_url = reverse("users")
        self.detail_url = reverse(
            "user-detail", kwargs={"public_id": self.other_user.public_id}
        )

    def test_viewer_can_view_users(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_viewer_cannot_modify_users(self):
        self.assertEqual(
            self.client.patch(self.detail_url, {"fname": "X"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

class UserSelfPermissionTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user.set_password("StrongP@ssw0rd!")
        cls.user.save()

        cls.detail_url = reverse(
            "user-detail", kwargs={"public_id": cls.user.public_id}
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_user_can_edit_self(self):
        resp = self.client.patch(
            self.detail_url,
            {"job_title": "Updated by self"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_cannot_delete_self(self):
        self.assertEqual( self.client.delete(self.detail_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED, )