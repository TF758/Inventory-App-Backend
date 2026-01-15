from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from db_inventory.factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
    UserFactory,
    UserLocationFactory,
    AccessoryFactory,
)
from db_inventory.models import AccessoryAssignment
from db_inventory.models.roles import RoleAssignment


class AccessoryAssignmentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.assign_url = reverse("assign-accessory")


class TestAssignAccessory(AccessoryAssignmentAPITestCase):

    def test_room_admin_can_assign_accessory_to_user_in_same_room(self):
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

        accessory = AccessoryFactory(room=room, quantity=10)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "accessory": accessory.public_id,
                "user": assignee.public_id,
                "quantity": 3,
                "notes": "Issued for work",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        accessory.refresh_from_db()
        self.assertEqual(accessory.available_quantity, 7)

        assignment = AccessoryAssignment.objects.get(
            accessory=accessory,
            user=assignee,
            returned_at__isnull=True,
        )
        self.assertEqual(assignment.quantity, 3)
    def test_assigning_again_to_same_user_aggregates_quantity(self):
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

        accessory = AccessoryFactory(room=room, quantity=10)

        # First assignment
        AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=3,
            assigned_by=admin,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "accessory": accessory.public_id,
                "user": user.public_id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        assignments = AccessoryAssignment.objects.filter(
            accessory=accessory,
            user=user,
            returned_at__isnull=True,
        )
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments.first().quantity, 5)

        accessory.refresh_from_db()
        self.assertEqual(accessory.available_quantity, 5)

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

        accessory = AccessoryFactory(room=room_a, quantity=5)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "accessory": accessory.public_id,
                "user": assignee.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            AccessoryAssignment.objects.filter(accessory=accessory).exists())
        
    def test_location_admin_cannot_assign_accessory_outside_location(self):
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

        accessory = AccessoryFactory(room=room_a, quantity=5)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "accessory": accessory.public_id,
                "user": assignee.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
    
    def test_assign_fails_if_quantity_exceeds_available(self):
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

        accessory = AccessoryFactory(room=room, quantity=5)

        # Existing assignment consumes 4
        AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=4,
            assigned_by=admin,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "accessory": accessory.public_id,
                "user": user.public_id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        accessory.refresh_from_db()
        self.assertEqual(accessory.available_quantity, 1)
    
    def test_assignment_fails_if_accessory_moved_out_of_scope(self):
        dept_a = DepartmentFactory()
        dept_b = DepartmentFactory()

        loc_a = LocationFactory(department=dept_a)
        loc_b = LocationFactory(department=dept_b)

        room_a = RoomFactory(location=loc_a)
        room_b = RoomFactory(location=loc_b)

        admin = UserFactory()
        RoleAssignment.objects.create(
            user=admin,
            role="LOCATION_ADMIN",
            location=loc_a,
        )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user = UserFactory()
        UserLocationFactory(user=user, room=room_a)

        accessory = AccessoryFactory(room=room_a, quantity=5)

        # Simulate relocation before assignment
        accessory.room = room_b
        accessory.save()

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.assign_url,
            {
                "accessory": accessory.public_id,
                "user": user.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)


class TestAdminReturnAccessory(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.return_url = reverse("admin-return-accessory")

    def test_admin_can_partially_return_accessory(self):
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

        accessory = AccessoryFactory(room=room, quantity=10)

        assignment = AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=5,
            assigned_by=admin,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.return_url,
            {
                "assignment": assignment.pk,
                "quantity": 2,
                "notes": "Returned unused",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        assignment.refresh_from_db()
        self.assertEqual(assignment.quantity, 3)
        self.assertIsNone(assignment.returned_at)

        accessory.refresh_from_db()
        self.assertEqual(accessory.available_quantity, 7)

    def test_admin_can_fully_return_accessory(self):
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

        accessory = AccessoryFactory(room=room, quantity=10)

        assignment = AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=4,
            assigned_by=admin,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.return_url,
            {
                "assignment": assignment.pk,
                "quantity": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        assignment.refresh_from_db()
        self.assertEqual(assignment.quantity, 0)
        self.assertIsNotNone(assignment.returned_at)

        accessory.refresh_from_db()
        self.assertEqual(accessory.available_quantity, 10)

    def test_admin_cannot_return_more_than_assigned(self):
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

        accessory = AccessoryFactory(room=room, quantity=10)

        assignment = AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=3,
            assigned_by=admin,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.return_url,
            {
                "assignment": assignment.pk,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        assignment.refresh_from_db()
        self.assertEqual(assignment.quantity, 3)
    
    def test_admin_cannot_return_closed_assignment(self):
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

        accessory = AccessoryFactory(room=room, quantity=10)

        assignment = AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=0,
            assigned_by=admin,
            returned_at=timezone.now(),
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.return_url,
            {
                "assignment": assignment.pk,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)