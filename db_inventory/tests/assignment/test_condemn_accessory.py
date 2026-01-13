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


class TestCondemnAccessory(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.condemn_url = reverse("condemn-accessory")

    def test_admin_can_condemn_available_accessories(self):
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

        accessory = AccessoryFactory(
            room=room,
            quantity=10,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.condemn_url,
            {
                "accessory": accessory.public_id,
                "quantity": 4,
                "notes": "Damaged stock",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        accessory.refresh_from_db()
        self.assertEqual(accessory.quantity, 6)


    def test_cannot_condemn_more_than_available_quantity(self):
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

        accessory = AccessoryFactory(
            room=room,
            quantity=5,
        )

        # Assign all stock
        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=5,
            assigned_by=admin,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.condemn_url,
            {
                "accessory": accessory.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned", str(response.data).lower())

        accessory.refresh_from_db()
        self.assertEqual(accessory.quantity, 5)

    
    def test_cannot_condemn_beyond_available_when_partially_assigned(self):
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

        accessory = AccessoryFactory(
            room=room,
            quantity=10,
        )

        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=7,
            assigned_by=admin,
        )

        # available_quantity = 3

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.condemn_url,
            {
                "accessory": accessory.public_id,
                "quantity": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        accessory.refresh_from_db()
        self.assertEqual(accessory.quantity, 10)

    
    def test_non_admin_cannot_condemn_accessory(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        accessory = AccessoryFactory(
            room=room,
            quantity=5,
        )

        self.client.force_authenticate(user)

        response = self.client.post(
            self.condemn_url,
            {
                "accessory": accessory.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        accessory.refresh_from_db()
        self.assertEqual(accessory.quantity, 5)

    def test_cannot_condemn_zero_quantity(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(user=admin, role="ROOM_ADMIN", room=room)
        admin.active_role = admin.role_assignments.first()
        admin.save()

        accessory = AccessoryFactory(room=room, quantity=5)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.condemn_url,
            {
                "accessory": accessory.public_id,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        accessory.refresh_from_db()
        self.assertEqual(accessory.quantity, 5)

    def test_admin_cannot_condemn_accessory_outside_scope(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)

        room_a = RoomFactory(location=loc)
        room_b = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(user=admin, role="ROOM_ADMIN", room=room_a)
        admin.active_role = admin.role_assignments.first()
        admin.save()

        accessory = AccessoryFactory(room=room_b, quantity=5)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.condemn_url,
            {
                "accessory": accessory.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        accessory.refresh_from_db()
        self.assertEqual(accessory.quantity, 5)