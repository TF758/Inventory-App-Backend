from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from access.models import Permission, RolePermission
from assets.models.assets import Equipment, EquipmentStatus
from assignments.models.asset_assignment import (
    EquipmentAssignment,
    ReturnRequest,
    ReturnRequestItem,
)
from sites.models.sites import Department, Location, Room, UserPlacement
from users.models.roles import RoleAssignment
from users.models.users import User


class ReturnRequestAPIPermissionTests(APITestCase):
    """
    Small API integration tests for return-request admin workflow permissions.

    This suite proves the custom action path:

        URL -> ViewSet action -> ReturnRequestPermission
        -> AccessService -> object scope / queryset scope
        -> response

    It intentionally does not fully test approve/deny/process business logic.
    That belongs to service tests.

    The goal here is to prove:

        - returns.view gates admin list/retrieve/pending
        - returns.process gates approve/deny/process actions
        - returns.view alone cannot process
        - returns.process can reach workflow endpoint logic
        - out-of-scope requests/items are denied or hidden
    """

    @classmethod
    def setUpTestData(cls):
        # --------------------------------------------------
        # Site hierarchy: in-scope
        # --------------------------------------------------

        cls.department = Department.objects.create(
            name="Engineering",
        )
        cls.location = Location.objects.create(
            name="Main Building",
            department=cls.department,
        )
        cls.room = Room.objects.create(
            name="Room 101",
            location=cls.location,
        )

        # --------------------------------------------------
        # Site hierarchy: outside scope
        # --------------------------------------------------

        cls.other_department = Department.objects.create(
            name="Science",
        )
        cls.other_location = Location.objects.create(
            name="Other Building",
            department=cls.other_department,
        )
        cls.other_room = Room.objects.create(
            name="Room 202",
            location=cls.other_location,
        )

        # --------------------------------------------------
        # Admin user scoped to Room 101
        # --------------------------------------------------

        cls.admin_user = User.objects.create_user(
            email="return-admin@example.com",
            password="password",
        )

        cls.admin_role = RoleAssignment.objects.create(
            user=cls.admin_user,
            role="ROOM_ADMIN",
            room=cls.room,
        )

        cls.admin_user.active_role = cls.admin_role
        cls.admin_user.save()

        # --------------------------------------------------
        # Requesting users
        # --------------------------------------------------

        cls.requester = User.objects.create_user(
            email="requester@example.com",
            password="password",
        )

        cls.other_requester = User.objects.create_user(
            email="other-requester@example.com",
            password="password",
        )

        UserPlacement.objects.create(
            user=cls.requester,
            room=cls.room,
            is_current=True,
        )

        UserPlacement.objects.create(
            user=cls.other_requester,
            room=cls.other_room,
            is_current=True,
        )

        # --------------------------------------------------
        # In-scope return request
        # --------------------------------------------------

        cls.in_scope_equipment = Equipment.objects.create(
            name="In Scope Laptop",
            brand="Dell",
            model="Latitude",
            serial_number="RR-EQ-IN-001",
            status=EquipmentStatus.OK,
            room=cls.room,
        )

        cls.in_scope_assignment = EquipmentAssignment.objects.create(
            equipment=cls.in_scope_equipment,
            user=cls.requester,
            assigned_by=cls.admin_user,
        )

        cls.in_scope_request = ReturnRequest.objects.create(
            requester=cls.requester,
            status=ReturnRequest.Status.PENDING,
            notes="Return in-scope equipment",
        )

        cls.in_scope_item = ReturnRequestItem.objects.create(
            return_request=cls.in_scope_request,
            item_type=ReturnRequestItem.ItemType.EQUIPMENT,
            equipment_assignment=cls.in_scope_assignment,
            room=cls.room,
            status=ReturnRequestItem.Status.PENDING,
        )

        # --------------------------------------------------
        # Outside-scope return request
        # --------------------------------------------------

        cls.outside_equipment = Equipment.objects.create(
            name="Outside Scope Laptop",
            brand="HP",
            model="EliteBook",
            serial_number="RR-EQ-OUT-001",
            status=EquipmentStatus.OK,
            room=cls.other_room,
        )

        cls.outside_assignment = EquipmentAssignment.objects.create(
            equipment=cls.outside_equipment,
            user=cls.other_requester,
            assigned_by=cls.admin_user,
        )

        cls.outside_request = ReturnRequest.objects.create(
            requester=cls.other_requester,
            status=ReturnRequest.Status.PENDING,
            notes="Return outside-scope equipment",
        )

        cls.outside_item = ReturnRequestItem.objects.create(
            return_request=cls.outside_request,
            item_type=ReturnRequestItem.ItemType.EQUIPMENT,
            equipment_assignment=cls.outside_assignment,
            room=cls.other_room,
            status=ReturnRequestItem.Status.PENDING,
        )

        # --------------------------------------------------
        # Already processed item.
        #
        # Used to prove item workflow permission reaches view logic
        # without invoking approve_return_item / deny_return_item.
        # --------------------------------------------------

        cls.processed_item = ReturnRequestItem.objects.create(
            return_request=cls.in_scope_request,
            item_type=ReturnRequestItem.ItemType.EQUIPMENT,
            equipment_assignment=cls.in_scope_assignment,
            room=cls.room,
            status=ReturnRequestItem.Status.APPROVED,
        )

        # --------------------------------------------------
        # URLs
        # --------------------------------------------------

        cls.list_url = reverse(
            "admin-return-request-list",
        )

        cls.pending_url = reverse(
            "admin-return-request-pending",
        )

        cls.in_scope_detail_url = reverse(
            "admin-return-request-detail",
            kwargs={
                "public_id": cls.in_scope_request.public_id,
            },
        )

        cls.outside_detail_url = reverse(
            "admin-return-request-detail",
            kwargs={
                "public_id": cls.outside_request.public_id,
            },
        )

        cls.in_scope_process_url = reverse(
            "admin-return-request-process",
            kwargs={
                "public_id": cls.in_scope_request.public_id,
            },
        )

        cls.outside_process_url = reverse(
            "admin-return-request-process",
            kwargs={
                "public_id": cls.outside_request.public_id,
            },
        )

        cls.in_scope_approve_url = reverse(
            "admin-return-request-approve",
            kwargs={
                "public_id": cls.in_scope_request.public_id,
            },
        )

        cls.in_scope_deny_url = reverse(
            "admin-return-request-deny",
            kwargs={
                "public_id": cls.in_scope_request.public_id,
            },
        )

        cls.item_approve_url = reverse(
            "admin-return-request-item-approve",
            kwargs={
                "public_id": cls.processed_item.public_id,
            },
        )

        cls.outside_item_approve_url = reverse(
            "admin-return-request-item-approve",
            kwargs={
                "public_id": cls.outside_item.public_id,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def grant_permission(
        cls,
        role,
        permission_code,
    ):
        permission, _ = Permission.objects.get_or_create(
            code=permission_code,
            defaults={
                "domain": permission_code.split(".")[0],
                "name": permission_code,
            },
        )

        RolePermission.objects.get_or_create(
            role=role,
            permission=permission,
        )

    def authenticate(
        self,
        user=None,
    ):
        self.client.force_authenticate(
            user=user or self.admin_user,
        )

    def get_rows(
        self,
        response,
    ):
        data = response.data

        if isinstance(data, dict) and "results" in data:
            return data["results"]

        return data

    # ------------------------------------------------------------------
    # Admin list / pending / retrieve: returns.view
    # ------------------------------------------------------------------

    def test_user_without_returns_view_cannot_list_return_requests(self):
        self.authenticate()

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_user_with_returns_view_can_list_in_scope_return_requests(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        rows = self.get_rows(
            response,
        )

        public_ids = {
            row["public_id"]
            for row in rows
        }

        self.assertIn(
            self.in_scope_request.public_id,
            public_ids,
        )
        self.assertNotIn(
            self.outside_request.public_id,
            public_ids,
        )

    def test_user_with_returns_view_can_list_pending_in_scope_return_requests(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.get(
            self.pending_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        rows = self.get_rows(
            response,
        )

        public_ids = {
            row["public_id"]
            for row in rows
        }

        self.assertIn(
            self.in_scope_request.public_id,
            public_ids,
        )
        self.assertNotIn(
            self.outside_request.public_id,
            public_ids,
        )

    def test_user_with_returns_view_can_retrieve_in_scope_return_request(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.get(
            self.in_scope_detail_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["public_id"],
            self.in_scope_request.public_id,
        )

        self.assertEqual(
            response.data["items"][0]["asset_public_id"],
            self.in_scope_equipment.public_id,
        )

    def test_user_with_returns_view_cannot_retrieve_outside_scope_return_request(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.get(
            self.outside_detail_url,
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ],
        )

    # ------------------------------------------------------------------
    # Workflow actions: returns.process
    # ------------------------------------------------------------------

    def test_returns_view_alone_cannot_process_return_request(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.post(
            self.in_scope_process_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_returns_view_alone_cannot_approve_return_request(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.post(
            self.in_scope_approve_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_returns_view_alone_cannot_deny_return_request(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.post(
            self.in_scope_deny_url,
            {
                "reason": "Not accepted.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_returns_process_can_reach_process_endpoint_logic(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.process",
        )
        self.authenticate()

        response = self.client.post(
            self.in_scope_process_url,
            {},
            format="json",
        )

        # This proves permission passed and the request reached the
        # business validation branch:
        #
        #     {"detail": "No items provided."}
        #
        # We are not testing full processing here.
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "No items provided.",
        )

    def test_returns_process_cannot_process_outside_scope_return_request(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.process",
        )
        self.authenticate()

        response = self.client.post(
            self.outside_process_url,
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ],
        )

    # ------------------------------------------------------------------
    # Item workflow actions
    # ------------------------------------------------------------------

    def test_returns_view_alone_cannot_approve_return_request_item(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.view",
        )
        self.authenticate()

        response = self.client.post(
            self.item_approve_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_returns_process_can_reach_item_workflow_endpoint_logic(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.process",
        )
        self.authenticate()

        response = self.client.post(
            self.item_approve_url,
            {},
            format="json",
        )

        # processed_item is already APPROVED, so reaching the view should
        # return the endpoint's own business validation response rather
        # than a permission denial.
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Return item already processed.",
        )

    def test_returns_process_cannot_approve_outside_scope_return_request_item(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "returns.process",
        )
        self.authenticate()

        response = self.client.post(
            self.outside_item_approve_url,
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ],
        )