from django.test import TransactionTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from db_inventory.factories import EquipmentFactory, RoomFactory, UserFactory
from db_inventory.models.asset_assignment import EquipmentAssignment
from db_inventory.models.roles import RoleAssignment
from db_inventory.models.security import Notification
from db_inventory.services.asset_returns import create_equipment_return_request
from db_inventory.models.audit import AuditLog

class AdminReturnItemWorkflowTests(TestCase):

    def setUp(self):

        self.client = APIClient()
        # users
        self.admin = UserFactory()
        self.user = UserFactory()
        # admin role
        self.admin_role = RoleAssignment.objects.create( user=self.admin, role="SITE_ADMIN" )
        self.admin.active_role = self.admin_role

        # location
        self.room = RoomFactory()

        # equipment
        self.equipment = EquipmentFactory(room=self.room)

        # assignment
        self.assignment = EquipmentAssignment.objects.create( equipment=self.equipment, user=self.user )
        # create return request
        self.return_request = create_equipment_return_request(
            user=self.user,
            equipment_public_ids=[self.equipment.public_id],
        )

        self.item = self.return_request.items.first()

        self.client.force_authenticate(self.admin)


    def test_admin_can_approve_return_item(self):

        url = reverse( "admin-return-item-approve", args=[self.item.public_id] )

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "approved")

    def test_admin_can_deny_return_item(self):

        url = reverse(
            "admin-return-item-deny",
            args=[self.item.public_id]
        )

        response = self.client.post( url, {"reason": "Damaged"}, format="json" )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "denied")

    
    def test_request_status_updates_after_item_approval(self):

        url = reverse( "admin-return-item-approve", args=[self.item.public_id] )

        self.client.post(url)
        self.return_request.refresh_from_db()
        self.assertEqual( self.return_request.status, "approved" )


    def test_item_cannot_be_processed_twice(self):

        url = reverse( "admin-return-item-approve", args=[self.item.public_id] )

        self.client.post(url)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)


    def test_audit_log_created_for_item_approval(self):

        url = reverse(
            "admin-return-item-approve",
            args=[self.item.public_id]
        )

        self.client.post(url)

        audit = AuditLog.objects.filter(
            target_id=self.item.public_id
        ).first()

        self.assertIsNotNone(audit)

    def test_partial_return_request_processing(self):
        """
        Simulate real audit scenario:
        A request contains multiple items and they are processed differently.
        """

        # create TWO new equipments
        equipment1 = EquipmentFactory(room=self.room)
        equipment2 = EquipmentFactory(room=self.room)

        EquipmentAssignment.objects.create(
            equipment=equipment1,
            user=self.user
        )

        EquipmentAssignment.objects.create(
            equipment=equipment2,
            user=self.user
        )

        # create request with the two new equipments
        rr = create_equipment_return_request(
            user=self.user,
            equipment_public_ids=[
                equipment1.public_id,
                equipment2.public_id
            ],
        )

        items = list(rr.items.all())

        item1 = items[0]
        item2 = items[1]

        approve_url = reverse(
            "admin-return-item-approve",
            args=[item1.public_id]
        )

        deny_url = reverse(
            "admin-return-item-deny",
            args=[item2.public_id]
        )

        # approve first item
        self.client.post(approve_url)

        # deny second item
        self.client.post(deny_url, {"reason": "Damaged"}, format="json")

        rr.refresh_from_db()

        # request should now be PARTIAL
        self.assertEqual(rr.status, "partial")