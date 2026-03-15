from django.test import TestCase
from django.urls import reverse, resolve
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.request import Request
from db_inventory.permissions.assets import CanRequestAssetReturn
from db_inventory.models import (
    EquipmentAssignment,
    AccessoryAssignment,
    ConsumableIssue,
)
from db_inventory.factories import AccessoryFactory, ConsumableFactory, EquipmentFactory, UserFactory
from rest_framework.views import APIView
from rest_framework.test import force_authenticate


class AssetReturnPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = CanRequestAssetReturn()
        self.user = UserFactory()
        self.equipment = EquipmentFactory()

        EquipmentAssignment.objects.create(
            equipment=self.equipment,
            user=self.user
        )

    def _make_drf_request(self, user, data):
        request = self.factory.post(
            "/me/equipment/return/",
            data,
            format="json"
        )
        force_authenticate(request, user=user)
        return APIView().initialize_request(request)

    def test_user_can_return_owned_equipment(self):
        request = self._make_drf_request(
            self.user,
            {"equipment": [self.equipment.public_id]},
        )
        allowed = self.permission.has_permission(request, None)
        self.assertTrue(allowed)

    def test_user_cannot_return_other_users_equipment(self):
        other_user = UserFactory()
        request = self._make_drf_request(
            other_user,
            {"equipment": [self.equipment.public_id]},
        )
        allowed = self.permission.has_permission(request, None)
        self.assertFalse(allowed)


class EquipmentReturnViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

        self.equipment = EquipmentFactory()
        EquipmentAssignment.objects.create(
            equipment=self.equipment,
            user=self.user
        )

    def test_user_can_submit_return_request(self):
        payload = {
            "equipment": [self.equipment.public_id]
        }
        url = reverse("self-return-equipment")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_limit_of_20_equipment(self):
        equipments = [EquipmentFactory() for _ in range(21)]

        for eq in equipments:
            EquipmentAssignment.objects.create(
                equipment=eq,
                user=self.user
            )

        payload = {
            "equipment": [eq.public_id for eq in equipments]
        }

        url = reverse("self-return-equipment")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_duplicate_equipment_ids(self):
        payload = {
            "equipment": [
                self.equipment.public_id,
                self.equipment.public_id
            ]
        }

        url = reverse("self-return-equipment")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 403)


class AccessoryReturnViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

        self.accessory = AccessoryFactory()
        AccessoryAssignment.objects.create(
            accessory=self.accessory,
            user=self.user,
            quantity=5
        )

    def test_accessory_return_success(self):
        payload = {
            "accessories": [
                {
                    "accessory_public_id": self.accessory.public_id,
                    "quantity": 2
                }
            ]
        }

        url = reverse("self-return-accessories")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_accessory_quantity_validation(self):
        payload = {
            "accessories": [
                {
                    "accessory_public_id": self.accessory.public_id,
                    "quantity": 999
                }
            ]
        }

        url = reverse("self-return-accessories")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)


class ConsumableReturnViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

        self.consumable = ConsumableFactory()
        ConsumableIssue.objects.create(
            consumable=self.consumable,
            user=self.user,
            quantity=10,
            issued_quantity=10
        )

    def test_consumable_return_success(self):
        payload = {
            "consumables": [
                {
                    "consumable_public_id": self.consumable.public_id,
                    "quantity": 3
                }
            ]
        }

        url = reverse("self-return-consumables")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_invalid_quantity(self):
        payload = {
            "consumables": [
                {
                    "consumable_public_id": self.consumable.public_id,
                    "quantity": 999
                }
            ]
        }

        url = reverse("self-return-consumables")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)