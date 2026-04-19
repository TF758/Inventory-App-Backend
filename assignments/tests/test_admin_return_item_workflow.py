from django.test import  TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from assignments.models.asset_assignment import EquipmentAssignment
from assets.asset_factories import EquipmentFactory
from users.factories.user_factories import UserFactory
from users.models.roles import RoleAssignment
from db_inventory.models.audit import AuditLog
from assignments.services.asset_returns import create_mixed_return_request
from sites.factories.site_factories import RoomFactory


class AdminReturnItemWorkflowTests(TestCase):
    """
    Tests item-level admin processing for return requests.

    Covers:
    - approving and denying individual items
    - request status propagation from item decisions
    - prevention of double-processing
    - audit logging
    - mixed (partial) outcomes across multiple items
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

        self.item = self.return_request.items.first()

        self.client.force_authenticate(self.admin)

    # -----------------------------------------------------
    # Approve item
    # -----------------------------------------------------

    def test_admin_can_approve_return_item(self):
        """
        Admin can approve a single return item.
        """

        url = reverse(
            "admin-return-request-item-approve",
            args=[self.item.public_id]
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "approved")

    # -----------------------------------------------------
    # Deny item
    # -----------------------------------------------------

    def test_admin_can_deny_return_item(self):
        """
        Admin can deny a return item with a reason.
        """

        url = reverse(
            "admin-return-request-item-deny",
            args=[self.item.public_id]
        )

        response = self.client.post(
            url,
            {"reason": "Damaged"},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "denied")

    # -----------------------------------------------------
    # Request status updates
    # -----------------------------------------------------

    def test_request_status_updates_after_item_approval(self):
        """
        When all items are approved, the parent request
        should transition to 'approved'.
        """

        url = reverse(
            "admin-return-request-item-approve",
            args=[self.item.public_id]
        )

        self.client.post(url)

        self.return_request.refresh_from_db()

        self.assertEqual(self.return_request.status, "approved")

    # -----------------------------------------------------
    # Prevent double processing
    # -----------------------------------------------------

    def test_item_cannot_be_processed_twice(self):
        """
        Once an item is processed, further actions on it
        should be rejected.
        """

        url = reverse(
            "admin-return-request-item-approve",
            args=[self.item.public_id]
        )

        self.client.post(url)
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    # -----------------------------------------------------
    # Audit logging
    # -----------------------------------------------------

    def test_audit_log_created_for_item_denial(self):
        """
        An audit log entry should be created when an item is denied.
        """

        url = reverse( "admin-return-request-item-deny", args=[self.item.public_id] )

        self.client.post(url, {"reason": "Damaged"}, format="json")

        audit = AuditLog.objects.filter(
            target_id=self.item.public_id
        ).first()

        self.assertIsNotNone(audit)

    # -----------------------------------------------------
    # Partial processing scenario
    # -----------------------------------------------------

    def test_partial_return_request_processing(self):
        """
        When multiple items in a request are processed differently
        (some approved, some denied), the request should be marked as 'partial'.
        """

        # create TWO new equipments
        equipment1 = EquipmentFactory(room=self.room)
        equipment2 = EquipmentFactory(room=self.room)

        EquipmentAssignment.objects.create( equipment=equipment1, user=self.user )

        EquipmentAssignment.objects.create( equipment=equipment2, user=self.user )

        rr = create_mixed_return_request(
            user=self.user,
            items_payload=[
                {
                    "asset_type": "equipment",
                    "public_id": equipment1.public_id
                },
                {
                    "asset_type": "equipment",
                    "public_id": equipment2.public_id
                }
            ],
        )

        items = list(rr.items.all())

        item1 = items[0]
        item2 = items[1]

        approve_url = reverse( "admin-return-request-item-approve", args=[item1.public_id] )

        deny_url = reverse( "admin-return-request-item-deny", args=[item2.public_id] )

        # approve first item
        self.client.post(approve_url)

        # deny second item
        self.client.post(
            deny_url,
            {"reason": "Damaged"},
            format="json"
        )

        rr.refresh_from_db()

        self.assertEqual(rr.status, "partial")