
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone

from db_inventory.factories import AdminUserFactory, EquipmentFactory, UserFactory
from assignments.models.asset_assignment import EquipmentAssignment, EquipmentEvent
from db_inventory.models.assets import EquipmentStatus
from db_inventory.models.audit import AuditLog
from db_inventory.models.roles import RoleAssignment




class BatchEquipmentStatusChangeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("batch-equipment-status-change")

        cls.admin = AdminUserFactory()

        # Create SITE_ADMIN role (no scope)
        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.admin,
            role="SITE_ADMIN",
            assigned_by=cls.admin,
        )

        # Persist active_role to DB
        cls.admin.active_role = cls.site_admin_role
        cls.admin.save(update_fields=["active_role"])

        cls.eq1 = EquipmentFactory(status=EquipmentStatus.OK)
        cls.eq2 = EquipmentFactory(status=EquipmentStatus.OK)
        cls.eq3 = EquipmentFactory(status=EquipmentStatus.DAMAGED)

    def setUp(self):
        # Fresh client per test (important)
        self.client = APIClient()

    def authenticate(self):
        self.client.force_authenticate(user=self.admin)

    # 1️⃣ All Success
    def test_batch_status_change_all_success(self):
        self.authenticate()

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ],
            "status": EquipmentStatus.DAMAGED,
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        self.eq1.refresh_from_db()
        self.eq2.refresh_from_db()

        self.assertEqual(self.eq1.status, EquipmentStatus.DAMAGED)
        self.assertEqual(self.eq2.status, EquipmentStatus.DAMAGED)

        self.assertEqual(response.data["success"], 2)
        self.assertEqual(response.data["skipped"], 0)
        self.assertEqual(response.data["failed"], 0)

        self.assertEqual(EquipmentEvent.objects.count(), 2)
        self.assertEqual(AuditLog.objects.count(), 2)

    def test_batch_status_change_skipped(self):
        self.authenticate()

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq3.public_id,  # already DAMAGED
            ],
            "status": EquipmentStatus.DAMAGED,
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        self.eq1.refresh_from_db()
        self.eq3.refresh_from_db()

        self.assertEqual(self.eq1.status, EquipmentStatus.DAMAGED)
        self.assertEqual(self.eq3.status, EquipmentStatus.DAMAGED)

        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["skipped"], 1)
        self.assertEqual(response.data["failed"], 0)

    # 3️⃣ Invalid Public ID
    def test_batch_status_change_invalid_id(self):
        self.authenticate()

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                "INVALID_ID",
            ],
            "status": EquipmentStatus.DAMAGED,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["failed"], 1)
        self.assertEqual(response.data["skipped"], 0)

    # 4️⃣ Permission Failure (Non-admin)
    def test_batch_status_change_permission_failure(self):
        from db_inventory.factories import UserFactory

        user = UserFactory()
        self.client.force_authenticate(user=user)

        payload = {
            "equipment_public_ids": [self.eq1.public_id],
            "status": EquipmentStatus.DAMAGED,
        }

        response = self.client.post(self.url, payload, format="json")

        self.eq1.refresh_from_db()
        self.assertEqual(self.eq1.status, EquipmentStatus.OK)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["success"], 0)
        self.assertEqual(response.data["failed"], 1)

    # 7️⃣ Duplicate IDs Deduped
    def test_batch_status_change_duplicate_ids(self):
        self.authenticate()

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq1.public_id,
                self.eq2.public_id,
            ],
            "status": EquipmentStatus.DAMAGED,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["success"], 2)
        self.assertEqual(response.data["failed"], 0)

        # Ensure only 2 events created (not 3)
        self.assertEqual(EquipmentEvent.objects.count(), 2)

    # 8️⃣ Partial Failure Does Not Rollback
    def test_batch_partial_failure_does_not_rollback(self):
        self.authenticate()

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                "BAD_ID",
                self.eq2.public_id,
            ],
            "status": EquipmentStatus.DAMAGED,
        }

        response = self.client.post(self.url, payload, format="json")

        self.eq1.refresh_from_db()
        self.eq2.refresh_from_db()

        self.assertEqual(self.eq1.status, EquipmentStatus.DAMAGED)
        self.assertEqual(self.eq2.status, EquipmentStatus.DAMAGED)

        self.assertEqual(response.data["success"], 2)
        self.assertEqual(response.data["failed"], 1)


class BatchAssignEquipmentTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("batch-assign-equipment")

        # Actor (SITE_ADMIN)
        cls.admin = AdminUserFactory()
        cls.admin_role = RoleAssignment.objects.create(
            user=cls.admin,
            role="SITE_ADMIN",
            assigned_by=cls.admin,
        )
        cls.admin.active_role = cls.admin_role
        cls.admin.save(update_fields=["active_role"])

        # Target user
        cls.target_user = UserFactory()

        # Equipment
        cls.eq1 = EquipmentFactory()
        cls.eq2 = EquipmentFactory()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    # 1️⃣ All Success
    def test_batch_assign_all_success(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ],
            "user_public_id": self.target_user.public_id,
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data["success"], 2)
        self.assertEqual(response.data["skipped"], 0)
        self.assertEqual(response.data["failed"], 0)

        self.assertEqual(EquipmentAssignment.objects.count(), 2)
        self.assertEqual(EquipmentEvent.objects.count(), 2)
        self.assertEqual(AuditLog.objects.count(), 2)

    # 2️⃣ Already Assigned → Skipped
    def test_batch_assign_skips_already_assigned(self):
        EquipmentAssignment.objects.create(
            equipment=self.eq1,
            user=self.target_user,
            assigned_by=self.admin,
        )

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ],
            "user_public_id": self.target_user.public_id,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["skipped"], 1)
        self.assertEqual(response.data["failed"], 0)

        self.assertEqual(EquipmentAssignment.objects.count(), 2)

    # 3️⃣ Invalid Equipment ID
    def test_batch_assign_invalid_equipment_id(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                "INVALID_ID",
            ],
            "user_public_id": self.target_user.public_id,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["failed"], 1)

    # 4️⃣ Duplicate IDs
    def test_batch_assign_duplicate_ids(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq1.public_id,
                self.eq2.public_id,
            ],
            "user_public_id": self.target_user.public_id,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 2)
        self.assertEqual(EquipmentAssignment.objects.count(), 2)

    # 8️⃣ Idempotency (Second Run Skips)
    def test_batch_assign_idempotent(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ],
            "user_public_id": self.target_user.public_id,
        }

        # First run
        self.client.post(self.url, payload, format="json")

        # Second run
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 0)
        self.assertEqual(response.data["skipped"], 2)
        self.assertEqual(EquipmentAssignment.objects.count(), 2)

    # 6️⃣ Jurisdiction Hard Failure
    def test_batch_assign_jurisdiction_failure(self):
        # Remove SITE_ADMIN role
        self.admin.active_role = None
        self.admin.save(update_fields=["active_role"])

        payload = {
            "equipment_public_ids": [self.eq1.public_id],
            "user_public_id": self.target_user.public_id,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(EquipmentAssignment.objects.count(), 0)

class BatchUnassignEquipmentTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("batch-unassign-equipment")

        # Actor (SITE_ADMIN)
        cls.admin = AdminUserFactory()
        cls.admin_role = RoleAssignment.objects.create(
            user=cls.admin,
            role="SITE_ADMIN",
            assigned_by=cls.admin,
        )
        cls.admin.active_role = cls.admin_role
        cls.admin.save(update_fields=["active_role"])

        # Assigned user
        cls.assigned_user = UserFactory()

        # Equipment
        cls.eq1 = EquipmentFactory()
        cls.eq2 = EquipmentFactory()

        # Active assignments
        EquipmentAssignment.objects.create(
            equipment=cls.eq1,
            user=cls.assigned_user,
            assigned_by=cls.admin,
        )

        EquipmentAssignment.objects.create(
            equipment=cls.eq2,
            user=cls.assigned_user,
            assigned_by=cls.admin,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    # 1️⃣ All Success
    def test_batch_unassign_all_success(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["success"], 2)
        self.assertEqual(response.data["skipped"], 0)
        self.assertEqual(response.data["failed"], 0)

        # Both assignments should now be returned
        self.assertEqual(
            EquipmentAssignment.objects.filter(returned_at__isnull=True).count(),
            0
        )

        self.assertEqual(EquipmentEvent.objects.count(), 2)
        self.assertEqual(AuditLog.objects.count(), 2)

    # 2️⃣ Skip Already Unassigned
    def test_batch_unassign_skips_unassigned(self):
        # Unassign one manually
        assignment = EquipmentAssignment.objects.get(equipment=self.eq1)
        assignment.returned_at = assignment.assigned_at
        assignment.save(update_fields=["returned_at"])

        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["skipped"], 1)
        self.assertEqual(response.data["failed"], 0)

    # 3️⃣ Invalid Equipment ID
    def test_batch_unassign_invalid_equipment_id(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                "INVALID_ID",
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["failed"], 1)

    # 4️⃣ Duplicate IDs
    def test_batch_unassign_duplicate_ids(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq1.public_id,
                self.eq2.public_id,
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 2)
        self.assertEqual(
            EquipmentAssignment.objects.filter(returned_at__isnull=True).count(),
            0
        )

    # 5️⃣ Idempotency
    def test_batch_unassign_idempotent(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                self.eq2.public_id,
            ]
        }

        # First run
        self.client.post(self.url, payload, format="json")

        # Second run
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 0)
        self.assertEqual(response.data["skipped"], 2)

    # 6️⃣ Partial Failure Does Not Rollback
    def test_batch_unassign_partial_failure(self):
        payload = {
            "equipment_public_ids": [
                self.eq1.public_id,
                "BAD_ID",
                self.eq2.public_id,
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.data["success"], 2)
        self.assertEqual(response.data["failed"], 1)

        # Both valid ones should still be unassigned
        self.assertEqual(
            EquipmentAssignment.objects.filter(returned_at__isnull=True).count(),
            0
        )