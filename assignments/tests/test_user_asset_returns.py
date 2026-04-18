from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from db_inventory.factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from django.utils import timezone
from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment, ReturnRequest, ReturnRequestItem
from users.factories.user_factories import UserFactory


class MixedAssetReturnViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

        # Equipment
        self.equipment = EquipmentFactory()
        EquipmentAssignment.objects.create(
            equipment=self.equipment,
            user=self.user
        )

        # Accessory
        self.accessory = AccessoryFactory()
        AccessoryAssignment.objects.create(
            accessory=self.accessory,
            user=self.user,
            quantity=5
        )

        # Consumable
        self.consumable = ConsumableFactory()
        ConsumableIssue.objects.create(
            consumable=self.consumable,
            user=self.user,
            quantity=10,
            issued_quantity=10
        )

    def test_user_can_submit_mixed_return_request(self):

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                },
                {
                    "asset_type": "accessory",
                    "public_id": self.accessory.public_id,
                    "quantity": 2
                },
                {
                    "asset_type": "consumable",
                    "public_id": self.consumable.public_id,
                    "quantity": 3
                }
            ]
        }

        url = reverse("self-return-assets")

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 201)

    def test_missing_quantity_fails(self):

        payload = {
            "items": [
                {
                    "asset_type": "accessory",
                    "public_id": self.accessory.public_id
                }
            ]
        }

        url = reverse("self-return-assets")

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_duplicate_items_fail(self):

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                },
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                }
            ]
        }

        url = reverse("self-return-assets")

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_user_cannot_return_unowned_asset(self):

        other_equipment = EquipmentFactory()

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": other_equipment.public_id
                }
            ]
        }

        url = reverse("self-return-assets")

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 403)

    def test_limit_of_20_items(self):

        items = []

        for _ in range(21):
            eq = EquipmentFactory()
            EquipmentAssignment.objects.create(
                equipment=eq,
                user=self.user
            )
            items.append({
                "asset_type": "equipment",
                "public_id": eq.public_id
            })

        payload = {"items": items}

        url = reverse("self-return-assets")

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 400)


    def test_mixed_ownership_fails_entire_request(self):
        other_equipment = EquipmentFactory()  # not assigned

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                },
                {
                    "asset_type": "equipment",
                    "public_id": other_equipment.public_id
                }
            ]
        }

        response = self.client.post(
            reverse("self-return-assets"),
            payload,
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_cannot_return_already_returned_asset(self):
        assignment = EquipmentAssignment.objects.get(
            equipment=self.equipment,
            user=self.user
        )
        assignment.returned_at = timezone.now()
        assignment.save()

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                }
            ]
        }

        response = self.client.post(
            reverse("self-return-assets"),
            payload,
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_quantity_edge_cases(self):

        url = reverse("self-return-assets")

        # quantity = 0
        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "asset_type": "accessory",
                        "public_id": self.accessory.public_id,
                        "quantity": 0
                    }
                ]
            },
            format="json"
        )
        self.assertEqual(response.status_code, 400)

        # negative quantity
        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "asset_type": "consumable",
                        "public_id": self.consumable.public_id,
                        "quantity": -1
                    }
                ]
            },
            format="json"
        )
        self.assertEqual(response.status_code, 400)

        # exceeds available
        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "asset_type": "accessory",
                        "public_id": self.accessory.public_id,
                        "quantity": 999
                    }
                ]
            },
            format="json"
        )
        self.assertEqual(response.status_code, 400)

        #  exact limit (should pass)
        response = self.client.post(
            url,
            {
                "items": [
                    {
                        "asset_type": "accessory",
                        "public_id": self.accessory.public_id,
                        "quantity": 5
                    }
                ]
            },
            format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_atomicity_when_one_item_fails(self):

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                },
                {
                    "asset_type": "accessory",
                    "public_id": self.accessory.public_id,
                    "quantity": 999  # invalid
                }
            ]
        }

        response = self.client.post(
            reverse("self-return-assets"),
            payload,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

        # Ensure NOTHING was created
        self.assertEqual(ReturnRequest.objects.count(), 0)
        self.assertEqual(ReturnRequestItem.objects.count(), 0)

    def test_same_payload_cannot_be_submitted_twice(self):

        payload = {
            "items": [
                {
                    "asset_type": "equipment",
                    "public_id": self.equipment.public_id
                }
            ]
        }

        url = reverse("self-return-assets")

        response1 = self.client.post(url, payload, format="json")
        response2 = self.client.post(url, payload, format="json")

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 400)