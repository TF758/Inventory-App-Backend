from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from django.urls import reverse
from db_inventory.factories import EquipmentFactory, RoomFactory, UserFactory
from db_inventory.models.asset_assignment import EquipmentAssignment, ReturnRequest
from db_inventory.permissions.assets import CanProcessReturnRequest
from db_inventory.models.roles import RoleAssignment
from db_inventory.models.security import Notification
from db_inventory.services.asset_returns import create_equipment_return_request

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

    # -----------------------------------------------------
    # Site admin should always be allowed
    # -----------------------------------------------------

    def test_site_admin_can_process_request(self):

        request = self.factory.post("/")
        request.user = self.admin

        allowed = self.permission.has_object_permission(
            request,
            None,
            self.return_request
        )

        self.assertTrue(allowed)

    # -----------------------------------------------------
    # Regular users cannot process requests
    # -----------------------------------------------------

    def test_regular_user_cannot_process_request(self):

        request = self.factory.post("/")
        request.user = self.user

        allowed = self.permission.has_object_permission(
            request,
            None,
            self.return_request
        )

        self.assertFalse(allowed)

    # -----------------------------------------------------
    # Anonymous users cannot process requests
    # -----------------------------------------------------

    def test_anonymous_user_denied(self):

        request = self.factory.post("/")
        request.user = None

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

        # create return request
        self.return_request = create_equipment_return_request(
            user=self.user,
            equipment_public_ids=[self.equipment.public_id],
        )

        self.client.force_authenticate(self.admin)

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

    def test_cannot_process_request_twice(self):

        url = reverse(
            "admin-return-request-approve",
            args=[self.return_request.public_id]
        )

        self.client.post(url)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)


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
        
    def test_admin_can_resolve_partial_request(self):

        item = self.return_request.items.first()

        url = reverse(
            "admin-return-request-resolve",
            args=[self.return_request.public_id]
        )

        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "id": item.public_id,
                        "action": "approve"
                    }
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
