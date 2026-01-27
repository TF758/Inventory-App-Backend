from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from db_inventory.factories import (
    RoomFactory,
    UserFactory,
    UserLocationFactory,
    AccessoryFactory,
)
from db_inventory.models import AccessoryAssignment
from db_inventory.models.roles import RoleAssignment
from db_inventory.tests.utils.assignments_test_bases import CondemnAccessoryTestBase


class TestCondemnAccessory(CondemnAccessoryTestBase):

    def setUp(self):
        super().setUp()
        self.authenticate_admin()

    def test_admin_can_condemn_available_accessories(self):
        accessory = AccessoryFactory(
            room=self.room,
            quantity=10,
        )

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
        accessory = AccessoryFactory(room=self.room, quantity=5)

        user = UserFactory()
        UserLocationFactory(user=user, room=self.room)

        AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=5,
            assigned_by=self.admin,
        )

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
        accessory = AccessoryFactory(room=self.room, quantity=10)

        user = UserFactory()
        UserLocationFactory(user=user, room=self.room)

        AccessoryAssignment.objects.create(
            accessory=accessory,
            user=user,
            quantity=7,
            assigned_by=self.admin,
        )

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
        self.client.force_authenticate(user=None)

        user = UserFactory()
        UserLocationFactory(user=user, room=self.room)

        accessory = AccessoryFactory(room=self.room, quantity=5)

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
        accessory = AccessoryFactory(room=self.room, quantity=5)

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
        other_room = RoomFactory(location=self.location)
        accessory = AccessoryFactory(room=other_room, quantity=5)

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
