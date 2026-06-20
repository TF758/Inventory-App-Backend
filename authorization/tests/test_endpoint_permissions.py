# departments/tests/test_department_permissions.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from authorization.models import Permission, RolePermission
from authorization.helpers import invalidate_role_permission_cache

from authorization.tests.utils import PermissionTestFixture

from sites.models.sites import Department

# TEST SITE MODULE

class DepartmentPermissionTests(APITestCase):

    @classmethod
    def setUpTestData(cls):

        fixture = PermissionTestFixture.build()

        cls.user = fixture["viewer"]
        cls.role = fixture["viewer_role"]

        cls.department = fixture["department"]

        cls.create_permission = Permission.objects.create(
            code="departments.create",
            name="Create Departments",
            module="departments",
        )

    def setUp(self):
        self.client.force_authenticate(
            user=self.user,
        )

    def test_create_department_requires_permission(self):

        url = reverse("departments")

        payload = {
            "name": "New Department",
        }

        # No permission
        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # Grant permission
        RolePermission.objects.create(
            role=self.role,
            permission=self.create_permission,
        )

        invalidate_role_permission_cache()

        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertNotEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
    
    # AGREEMENT MODUEL - COVERAG

    def test_agreement_coverage_create_requires_agreement_update_permission(self):

        url = reverse("coverages")

        # No permission
        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        update_permission = Permission.objects.create(
            code="agreements.update",
            name="Update Agreements",
            module="agreements",
        )

        RolePermission.objects.create(
            role=self.role,
            permission=update_permission,
        )

        invalidate_role_permission_cache()

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertNotEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
    

    def test_agreement_item_attach_requires_attach_permission(self):

        url = reverse(
            "attach-agreement-item"
        )

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        permission = Permission.objects.create(
            code="agreements.attach_items",
            name="Attach Agreement Items",
            module="agreements",
        )

        RolePermission.objects.create(
            role=self.role,
            permission=permission,
        )

        invalidate_role_permission_cache()

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertNotEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )