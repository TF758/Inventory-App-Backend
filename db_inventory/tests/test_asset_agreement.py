from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from db_inventory.models.assets import  AssetAgreementItem
from db_inventory.factories import AssetAgreementFactory, DepartmentFactory, EquipmentFactory, LocationFactory, RoomFactory, UserFactory, AssetAgreementItemFactory
from db_inventory.models.roles import RoleAssignment


class AssetAgreementPermissionTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.department = DepartmentFactory()
        self.location = LocationFactory(department=self.department)
        self.room = RoomFactory(location=self.location)

        self.agreement = AssetAgreementFactory(
            department=self.department
        )

        self.list_url = reverse("agreements")

        self.detail_url = reverse(
            "agreement-detail",
            kwargs={"public_id": self.agreement.public_id}
        )

    def _assign_role(self, user, role_name, department=None, location=None, room=None):

        role = RoleAssignment.objects.create(
            user=user,
            role=role_name,
            department=department,
            location=location,
            room=room,
        )

        user.active_role = role
        user.save(update_fields=["active_role"])

        self.client.force_authenticate(user=user)

        return role

    def test_room_admin_can_view_agreements(self):

        user = UserFactory()

        self._assign_role(user, "ROOM_ADMIN", room=self.room)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_room_admin_cannot_create_agreement(self):

        user = UserFactory()

        self._assign_role(user, "ROOM_ADMIN", room=self.room)

        response = self.client.post(self.list_url, {
            "name": "Test Agreement",
            "agreement_type": "contract",
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_admin_can_create_agreement(self):

        user = UserFactory()

        self._assign_role(user, "LOCATION_ADMIN", location=self.location)

        response = self.client.post(self.list_url, {
            "name": "Location Contract",
            "agreement_type": "contract",
            "location": self.location.public_id
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_location_admin_cannot_delete_agreement(self):

        user = UserFactory()

        self._assign_role(user, "LOCATION_ADMIN", location=self.location)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_admin_can_delete_agreement(self):

        user = UserFactory()

        self._assign_role(user, "DEPARTMENT_ADMIN", department=self.department)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

class AssetAgreementScopeTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.department = DepartmentFactory()
        self.other_department = DepartmentFactory()

        self.location = LocationFactory(department=self.department)
        self.room = RoomFactory(location=self.location)

        self.agreement = AssetAgreementFactory(
            department=self.department
        )

        self.url = reverse("agreements")

    def _assign_role(self, user, role_name, department=None, location=None, room=None):

        role = RoleAssignment.objects.create(
            user=user,
            role=role_name,
            department=department,
            location=location,
            room=room,
        )

        user.active_role = role
        user.save(update_fields=["active_role"])

        self.client.force_authenticate(user=user)

        return role

    def test_user_cannot_see_agreements_outside_scope(self):

        user = UserFactory()

        self._assign_role(user, "DEPARTMENT_ADMIN", department=self.other_department)

        response = self.client.get(self.url)

        data = response.json()
        results = data.get("results", data)

        self.assertEqual(len(results), 0)

    def test_department_admin_can_see_department_agreements(self):

        user = UserFactory()

        self._assign_role(user, "DEPARTMENT_ADMIN", department=self.department)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)

        self.assertEqual(len(results), 1)
    
class AssetAgreementItemTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.department = DepartmentFactory()
        self.location = LocationFactory(department=self.department)
        self.room = RoomFactory(location=self.location)

        self.agreement = AssetAgreementFactory(
            department=self.department
        )

        self.equipment = EquipmentFactory(room=self.room)

        self.list_url = reverse("agreement-items")

    def _assign_role(self, user, role_name, department=None, location=None, room=None):

        role = RoleAssignment.objects.create(
            user=user,
            role=role_name,
            department=department,
            location=location,
            room=room,
        )

        user.active_role = role
        user.save(update_fields=["active_role"])

        self.client.force_authenticate(user=user)

        return role

    def _login_department_admin(self):

        user = UserFactory()

        self._assign_role(
            user,
            "DEPARTMENT_ADMIN",
            department=self.department
        )

        return user

    def test_department_admin_can_attach_asset(self):

        self._login_department_admin()

        response = self.client.post(self.list_url, {
            "agreement": self.agreement.public_id,
            "asset_public_id": self.equipment.public_id,
            "quantity": 1
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            AssetAgreementItem.objects.filter(
                agreement=self.agreement
            ).exists()
        )

    def test_attach_asset_outside_scope_fails(self):

        self._login_department_admin()

        other_department = DepartmentFactory()
        other_location = LocationFactory(department=other_department)
        other_room = RoomFactory(location=other_location)

        equipment = EquipmentFactory(room=other_room)

        response = self.client.post(self.list_url, {
            "agreement": self.agreement.public_id,
            "asset_public_id": equipment.public_id,
            "quantity": 1
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_agreement_items(self):

        self._login_department_admin()

        AssetAgreementItemFactory(
            agreement=self.agreement,
            equipment=self.equipment
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)

        self.assertEqual(len(results), 1)

    def test_delete_agreement_item(self):

        self._login_department_admin()

        item = AssetAgreementItemFactory(
            agreement=self.agreement,
            equipment=self.equipment
        )

        detail_url = reverse(
            "agreement-item-detail",
            kwargs={"pk": item.id}
        )

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(
            AssetAgreementItem.objects.filter(id=item.id).exists()
        )

    def test_duplicate_asset_in_agreement_fails(self):

        self._login_department_admin()

        AssetAgreementItemFactory(
            agreement=self.agreement,
            equipment=self.equipment
        )

        response = self.client.post(self.list_url, {
            "agreement": self.agreement.public_id,
            "asset_public_id": self.equipment.public_id,
            "quantity": 1
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)