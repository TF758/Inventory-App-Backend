from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from db_inventory.models import User, RoleAssignment, Department
from db_inventory.factories import AdminUserFactory, DepartmentFactory, LocationFactory, UserFactory, RoomFactory
from rest_framework.test import force_authenticate


class UserPermissionSiteAdminTest(APITestCase):

    def setUp(self):
        self.site_admin = AdminUserFactory()
        role = RoleAssignment.objects.create(
            user=self.site_admin,
            role="SITE_ADMIN",
            assigned_by=self.site_admin,
        )
        self.site_admin.active_role = role
        self.site_admin.save()

        self.client.force_authenticate(self.site_admin)

        self.target_user = UserFactory()

        self.list_url = reverse("users")
        self.detail_url = reverse(
            "user-detail", kwargs={"public_id": self.target_user.public_id}
        )

    def test_site_admin_can_view_users(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.get(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_site_admin_cannot_create_users_here(self):
        resp = self.client.post(self.list_url, {})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_site_admin_cannot_delete_users_here(self):
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

class DepartmentAdminUserPermissionTest(APITestCase):

    def setUp(self):
        self.department = DepartmentFactory()

        self.admin = UserFactory()
        role = RoleAssignment.objects.create(
            user=self.admin,
            role="DEPARTMENT_ADMIN",
            department=self.department,
            assigned_by=self.admin,
        )
        self.admin.active_role = role
        self.admin.save()

        self.user = UserFactory()

        self.client.force_authenticate(self.admin)

        self.list_url = reverse("users")
        self.detail_url = reverse(
            "user-detail", kwargs={"public_id": self.user.public_id}
        )

    def test_department_admin_can_view_users(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_department_admin_cannot_modify_users_here(self):
        self.assertEqual(
            self.client.post(self.list_url, {}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertEqual(
            self.client.patch(self.detail_url, {"fname": "X"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            self.client.delete(self.detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

class LocationAdminUserPermissionTest(APITestCase):

    def setUp(self):
        dept = DepartmentFactory()
        location = LocationFactory(department=dept)

        self.admin = UserFactory()
        role = RoleAssignment.objects.create(
            user=self.admin,
            role="LOCATION_ADMIN",
            location=location,
        )
        self.admin.active_role = role
        self.admin.save()

        self.target_user = UserFactory()

        self.client.force_authenticate(self.admin)

        self.list_url = reverse("users")
        self.detail_url = reverse(
            "user-detail", kwargs={"public_id": self.target_user.public_id}
        )

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

    def setUp(self):
        self.user = UserFactory()
        self.user.set_password("StrongP@ssw0rd!")
        self.user.save()

        self.client.force_authenticate(self.user)

        self.detail_url = reverse(
            "user-detail", kwargs={"public_id": self.user.public_id}
        )

    def test_user_can_edit_self(self):
        resp = self.client.patch(
            self.detail_url,
            {"job_title": "Updated by self"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_cannot_delete_self(self):
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
