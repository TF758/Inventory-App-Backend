from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from django.urls import reverse
from assignments.models.asset_assignment import EquipmentAssignment, ReturnRequest
from db_inventory.permissions.assets import CanProcessReturnRequest
from assets.asset_factories import EquipmentFactory
from users.factories.user_factories import UserFactory
from users.models.roles import RoleAssignment
from db_inventory.models.notifications import Notification
from django.contrib.auth.models import AnonymousUser
from assignments.services.asset_returns import create_mixed_return_request
from sites.factories.site_factories import RoomFactory

class CanProcessReturnRequestTests(TestCase):
    """
    Tests the CanProcessReturnRequest permission logic.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = CanProcessReturnRequest()

        self.admin = UserFactory()
        self.user = UserFactory()

        # assign site admin role
        self.admin_role = RoleAssignment.objects.create(
            user=self.admin,
            role="SITE_ADMIN"
        )

        self.admin.active_role = self.admin_role

        self.room = RoomFactory()
        self.equipment = EquipmentFactory(room=self.room)

        self.assignment = EquipmentAssignment.objects.create(
            equipment=self.equipment,
            user=self.user
        )

        self.return_request = ReturnRequest.objects.create(
            requester=self.user
        )

    def test_site_admin_can_process_request(self):
        request = self.factory.post("/")
        request.user = self.admin

        allowed = self.permission.has_object_permission(
            request,
            None,
            self.return_request
        )

        self.assertTrue(allowed)

    def test_regular_user_cannot_process_request(self):
        request = self.factory.post("/")
        request.user = self.user

        allowed = self.permission.has_object_permission(
            request,
            None,
            self.return_request
        )

        self.assertFalse(allowed)

    def test_anonymous_user_denied(self):
        request = self.factory.post("/")
        request.user = AnonymousUser()

        allowed = self.permission.has_object_permission(
            request,
            None,
            self.return_request
        )

        self.assertFalse(allowed)


class AdminReturnRequestWorkflowTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # users
        self.admin = UserFactory()
        self.user = UserFactory()

        # admin role
        self.admin_role = RoleAssignment.objects.create(
            user=self.admin,
            role="SITE_ADMIN"
        )

        self.admin.active_role = self.admin_role
        self.admin.save()

        # location
        self.room = RoomFactory()

        # equipment
        self.equipment = EquipmentFactory(room=self.room)

        # assignment
        self.assignment = EquipmentAssignment.objects.create(
            equipment=self.equipment,
            user=self.user
        )


        self.return_request = create_mixed_return_request(
            user=self.user,
            items_payload=[
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                }
            ],
        )

        self.client.force_authenticate(self.admin)

    # -----------------------------------------------------
    # Approve request
    # -----------------------------------------------------

    def test_admin_can_approve_return_request(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        self.return_request.refresh_from_db()

        self.assertEqual(
            self.return_request.status,
            "approved"
        )

    # -----------------------------------------------------
    # Cannot process twice
    # -----------------------------------------------------

    def test_cannot_process_request_twice(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        self.client.post(url)
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    # -----------------------------------------------------
    # Notification created
    # -----------------------------------------------------

    def test_notification_created_on_approval(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        self.client.post(url)

        notification = Notification.objects.filter(
            recipient=self.user
        ).first()

        self.assertIsNotNone(notification)

        self.assertEqual(
            notification.title,
            "Return Request Approved"
        )

    # -----------------------------------------------------
    # Process via batch (partial / full)
    # -----------------------------------------------------

    def test_admin_can_resolve_request(self):

        items = list(self.return_request.items.all())

        url = reverse(
            "admin-return-request-process",
            args=[self.return_request.public_id]
        )

        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "public_id": item.public_id,
                        "action": "approve"
                    }
                    for item in items
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        self.return_request.refresh_from_db()

        self.assertEqual(
            self.return_request.status,
            "approved"
        )

class AdminReturnRequestWorkflowTests(TestCase):

    """
    Tests admin workflows for processing return requests.

    Validates approval, duplicate processing prevention, batch item processing,
    status transitions, and notification side effects.
    """

    def setUp(self):

        self.client = APIClient()

        # users
        self.admin = UserFactory()
        self.user = UserFactory()

        # admin role
        self.admin_role = RoleAssignment.objects.create(
            user=self.admin,
            role="SITE_ADMIN"
        )

        self.admin.active_role = self.admin_role
        self.admin.save()

        # location
        self.room = RoomFactory()

        self.equipment = EquipmentFactory(room=self.room)

        self.assignment = EquipmentAssignment.objects.create(
            equipment=self.equipment,
            user=self.user
        )

        self.return_request = create_mixed_return_request(
            user=self.user,
            items_payload=[
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                }
            ],
        )

        self.client.force_authenticate(self.admin)

    # -----------------------------------------------------
    # Approve request
    # -----------------------------------------------------

    def test_admin_can_approve_return_request(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        self.return_request.refresh_from_db()

        self.assertEqual(self.return_request.status, "approved")

    # -----------------------------------------------------
    # Cannot process twice
    # -----------------------------------------------------

    def test_cannot_process_request_twice(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        self.client.post(url)
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    # -----------------------------------------------------
    # Notification created
    # -----------------------------------------------------

    def test_notification_created_on_approval(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        self.client.post(url)

        notification = Notification.objects.filter(
            recipient=self.user
        ).first()

        self.assertIsNotNone(notification)

        self.assertEqual(notification.title, "Return Request Approved")

    # -----------------------------------------------------
    # Process request (batch)
    # -----------------------------------------------------

    def test_admin_can_process_request(self):

        items = list(self.return_request.items.all())

        url = reverse(
            "admin-return-request-process",
            args=[self.return_request.public_id]
        )

        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "public_id": item.public_id,
                        "action": "approve"
                    }
                    for item in items
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        self.return_request.refresh_from_db()

        self.assertEqual(self.return_request.status, "approved")