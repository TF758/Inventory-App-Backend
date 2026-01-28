from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from db_inventory.factories import DepartmentFactory, EquipmentFactory, LocationFactory, RoomFactory, UserFactory, UserLocationFactory
from db_inventory.models.asset_assignment import EquipmentAssignment
from db_inventory.models.assets import EquipmentStatus
from db_inventory.models.roles import RoleAssignment
from db_inventory.tests.utils.assignments_test_bases import EquipmentAssignmentAPITestBase

class TestAssignEquipment(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_room_admin_can_assign_equipment_to_user_in_same_room(self):
        assignee = UserFactory()
        UserLocationFactory(user=assignee, room=self.room)

        equipment = EquipmentFactory(room=self.room)

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": assignee.public_id,
                "notes": "Issued for work",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        equipment.refresh_from_db()
        self.assertTrue(equipment.is_assigned)

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, assignee)

    def test_room_admin_cannot_assign_to_user_outside_room(self):
        other_room = RoomFactory(location=self.location)

        assignee = UserFactory()
        UserLocationFactory(user=assignee, room=other_room)

        equipment = EquipmentFactory(room=self.room)

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": assignee.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        equipment.refresh_from_db()
        self.assertFalse(equipment.is_assigned)


class TestReassignEquipment(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_reassign_equipment_within_scope(self):
        user_a = UserFactory()
        user_b = UserFactory()
        UserLocationFactory(user=user_a, room=self.room)
        UserLocationFactory(user=user_b, room=self.room)

        equipment = EquipmentFactory(room=self.room)
        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user_a,
            assigned_by=self.admin,
        )

        response = self.client.post(
            self.reassign_url,
            {
                "equipment_id": equipment.public_id,
                "from_user_id": user_a.public_id,
                "to_user_id": user_b.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, user_b)

    def test_reassign_to_user_outside_scope_fails(self):
        other_room = RoomFactory(location=self.location)

        user_a = UserFactory()
        user_b = UserFactory()
        UserLocationFactory(user=user_a, room=self.room)
        UserLocationFactory(user=user_b, room=other_room)

        equipment = EquipmentFactory(room=self.room)
        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user_a,
            assigned_by=self.admin,
        )

        response = self.client.post(
            self.reassign_url,
            {
                "equipment_id": equipment.public_id,
                "from_user_id": user_a.public_id,
                "to_user_id": user_b.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, user_a)

class TestUnassignEquipment(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_unassign_equipment(self):
        user = UserFactory()
        UserLocationFactory(user=user, room=self.room)

        equipment = EquipmentFactory(room=self.room)
        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user,
            assigned_by=self.admin,
        )

        response = self.client.post(
            self.unassign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": user.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        equipment.refresh_from_db()
        self.assertFalse(equipment.is_assigned)

class TestEquipmentAssignmentEdgeCases(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_assignment_fails_if_equipment_moved_out_of_scope(self):
        other_location = LocationFactory(department=self.department)
        other_room = RoomFactory(location=other_location)

        user = UserFactory()
        UserLocationFactory(user=user, room=self.room)

        equipment = EquipmentFactory(room=self.room)

        equipment.room = other_room
        equipment.save()

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": user.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        equipment.refresh_from_db()
        self.assertFalse(equipment.is_assigned)


class TestEquipmentAssignmentGuards(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_assign_fails_if_equipment_already_assigned(self):
        user_a = UserFactory()
        user_b = UserFactory()
        UserLocationFactory(user=user_a, room=self.room)
        UserLocationFactory(user=user_b, room=self.room)

        equipment = EquipmentFactory(room=self.room)
        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user_a,
            assigned_by=self.admin,
        )

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": user_b.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, user_a)

    def test_reassign_to_same_user_fails(self):
        user = UserFactory()
        UserLocationFactory(user=user, room=self.room)

        equipment = EquipmentFactory(room=self.room)
        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user,
            assigned_by=self.admin,
        )

        response = self.client.post(
            self.reassign_url,
            {
                "equipment_id": equipment.public_id,
                "from_user_id": user.public_id,
                "to_user_id": user.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, user)

class TestAssignEquipmentLocationAdmin(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()

        # Switch admin role to LOCATION_ADMIN
        self.admin_role = RoleAssignment.objects.create(
            user=self.admin,
            role="LOCATION_ADMIN",
            location=self.location,
        )
        self.admin.active_role = self.admin_role
        self.admin.save()

        self.client.force_authenticate(user=self.admin)

    def test_location_admin_cannot_assign_equipment_outside_location(self):
        other_location = LocationFactory(department=self.department)
        other_room = RoomFactory(location=other_location)

        assignee = UserFactory()
        UserLocationFactory(user=assignee, room=other_room)

        equipment = EquipmentFactory(room=other_room)

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": assignee.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        equipment.refresh_from_db()
        self.assertFalse(equipment.is_assigned)

class TestEquipmentAssignmentUnassignGuards(EquipmentAssignmentAPITestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_unassign_fails_if_wrong_user(self):
        assigned_user = UserFactory()
        other_user = UserFactory()

        UserLocationFactory(user=assigned_user, room=self.room)
        UserLocationFactory(user=other_user, room=self.room)

        equipment = EquipmentFactory(room=self.room)

        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=assigned_user,
            assigned_by=self.admin,
        )

        response = self.client.post(
            self.unassign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": other_user.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        equipment.refresh_from_db()
        self.assertTrue(equipment.is_assigned)

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, assigned_user)