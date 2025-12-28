from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from db_inventory.factories import DepartmentFactory, EquipmentFactory, LocationFactory, RoomFactory, UserFactory, UserLocationFactory
from db_inventory.models.asset_assignment import EquipmentAssignment
from db_inventory.models.assets import EquipmentStatus
from db_inventory.models.roles import RoleAssignment

class EquipmentAssignmentAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.assign_url = reverse('assign-equipment')
        self.unassign_url =  reverse('unassign-equipment')
        self.reassign_url = reverse('reassign-equipment')

class TestAssignEquipment(EquipmentAssignmentAPITestCase):

   
    def setUp(self):
        super().setUp()
        self.assign_url = reverse("assign-equipment")
        self.unassign_url = reverse("unassign-equipment")
        self.reassign_url = reverse("reassign-equipment")

    def test_room_admin_can_assign_equipment_to_user_in_same_room(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="ROOM_ADMIN",
            room=room,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        assignee = UserFactory()
        UserLocationFactory(user=assignee, room=room)

        equipment = EquipmentFactory(room=room)

        self.client.force_authenticate(admin)

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

        assignment = EquipmentAssignment.objects.get(equipment=equipment)
        self.assertEqual(assignment.user, assignee)

        equipment.refresh_from_db()
        self.assertEqual(equipment.status, EquipmentStatus.ASSIGNED)
    
    def test_room_admin_cannot_assign_to_user_outside_room(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)

        room_a = RoomFactory(location=loc)
        room_b = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="ROOM_ADMIN",
            room=room_a,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        assignee = UserFactory()
        UserLocationFactory(user=assignee, room=room_b)

        equipment = EquipmentFactory(room=room_a)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": assignee.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("jurisdiction", str(response.data).lower())

    def test_location_admin_cannot_assign_equipment_outside_location(self):
        dept = DepartmentFactory()

        loc_a = LocationFactory(department=dept)
        loc_b = LocationFactory(department=dept)

        room_a = RoomFactory(location=loc_a)
        room_b = RoomFactory(location=loc_b)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="LOCATION_ADMIN",
            location=loc_b,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        assignee = UserFactory()
        UserLocationFactory(user=assignee, room=room_b)

        equipment = EquipmentFactory(room=room_a)

        self.client.force_authenticate(admin)


        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": assignee.public_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

class TestReassignEquipment(EquipmentAssignmentAPITestCase):

    
    def setUp(self):
        super().setUp()
        self.assign_url = reverse("assign-equipment")
        self.unassign_url = reverse("unassign-equipment")
        self.reassign_url = reverse("reassign-equipment")

    def test_reassign_equipment_within_scope(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="ROOM_ADMIN",
            room=room,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user_a = UserFactory()
        user_b = UserFactory()
        UserLocationFactory(user=user_a, room=room)
        UserLocationFactory(user=user_b, room=room)

        equipment = EquipmentFactory(room=room)

        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user_a,
            assigned_by=admin,
        )
        equipment.status = EquipmentStatus.ASSIGNED
        equipment.save()

        self.client.force_authenticate(admin)

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
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)

        room_a = RoomFactory(location=loc)
        room_b = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="ROOM_ADMIN",
            room=room_a,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user_a = UserFactory()
        user_b = UserFactory()
        UserLocationFactory(user=user_a, room=room_a)
        UserLocationFactory(user=user_b, room=room_b)

        equipment = EquipmentFactory(room=room_a)

        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user_a,
            assigned_by=admin,
        )
        equipment.status = EquipmentStatus.ASSIGNED
        equipment.save()

        self.client.force_authenticate(admin)

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

class TestUnassignEquipment(EquipmentAssignmentAPITestCase):

    def test_unassign_equipment(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="ROOM_ADMIN",
            room=room,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        equipment = EquipmentFactory(room=room)

        EquipmentAssignment.objects.create(
            equipment=equipment,
            user=user,
            assigned_by=admin,
        )
        equipment.status = EquipmentStatus.ASSIGNED
        equipment.save()

        self.client.force_authenticate(admin)

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
        self.assertEqual(equipment.status, EquipmentStatus.AVAILABLE)

class TestAssignEquipmentEdgeCases(EquipmentAssignmentAPITestCase):

    def test_assignment_fails_if_equipment_moved_to_other_location(self):
        """
        If equipment changes jurisdiction before assignment is committed,
        the assignment should fail.
        """

        # Department / location setup
        dept_a = DepartmentFactory()
        dept_b = DepartmentFactory()

        loc_a = LocationFactory(department=dept_a)
        loc_b = LocationFactory(department=dept_b)

        room_a = RoomFactory(location=loc_a)
        room_b = RoomFactory(location=loc_b)

        # Admin with authority over Location A
        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="LOCATION_ADMIN",
            location=loc_a,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        # User in Location A
        user = UserFactory()
        UserLocationFactory(user=user, room=room_a)

        # Equipment initially in Location A
        equipment = EquipmentFactory(room=room_a)

        self.client.force_authenticate(admin)

        # Simulate relocation BEFORE assignment
        equipment.room = room_b
        equipment.save()

        response = self.client.post(
            self.assign_url,
            {
                "equipment_id": equipment.public_id,
                "user_id": user.public_id,
            },
            format="json",
        )

        # EXPECTED SAFE BEHAVIOR
        self.assertEqual(response.status_code, 403)
        self.assertIn("detail", response.data)