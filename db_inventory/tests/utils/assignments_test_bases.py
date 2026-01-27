from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from django.test import TestCase

from db_inventory.factories import DepartmentFactory, LocationFactory, RoomFactory, UserFactory
from db_inventory.models.roles import RoleAssignment

class AccessoryAssignmentTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        role = RoleAssignment.objects.create(
            user=cls.admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.admin.active_role = role
        cls.admin.save()

        cls.assign_url = reverse("assign-accessory")
        cls.return_url = reverse("return-accessory")

    def authenticate_admin(self):
        # APITestCase already gives APIClient
        self.client.force_authenticate(user=self.admin)

class CondemnAccessoryTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        role = RoleAssignment.objects.create(
            user=cls.admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.admin.active_role = role
        cls.admin.save()

        cls.condemn_url = reverse("condemn-accessory")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)

class ConsumableAPITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        role = RoleAssignment.objects.create(
            user=cls.admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.admin.active_role = role
        cls.admin.save()

        cls.issue_url = reverse("issue-consumable")
        cls.use_url = reverse("use-consumable")
        cls.return_url = reverse("return-consumable")
        cls.report_loss_url = reverse("report-consumable-loss")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)


class EquipmentAssignmentAPITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        role = RoleAssignment.objects.create(
            user=cls.admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.admin.active_role = role
        cls.admin.save()

        cls.assign_url = reverse("assign-equipment")
        cls.unassign_url = reverse("unassign-equipment")
        cls.reassign_url = reverse("reassign-equipment")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)
