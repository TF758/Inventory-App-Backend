# assets/tests/api/test_equipment_api_permissions.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from access.models import Permission, RolePermission
from assets.models.assets import Equipment, EquipmentStatus
from sites.models.sites import Department, Location, Room
from users.models.users import User
from users.models.roles import RoleAssignment


class EquipmentAPIPermissionTests(APITestCase):
    """
    Small API integration tests for the standard scoped CRUD asset pattern.

    This suite proves the real request path:

        URL -> EquipmentModelViewSet -> AssetPermission
        -> AccessService -> ScopeFilterMixin / ScopeService
        -> serializer / response

    It intentionally does not retest every role/scope combination. Those are
    covered by service and permission unit tests.
    """

    @classmethod
    def setUpTestData(cls):
        # -------------------------
        # Site hierarchy
        # -------------------------

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

        # -------------------------
        # Equipment
        # -------------------------

        cls.in_scope_equipment = Equipment.objects.create(
            name="In Scope Laptop",
            brand="Dell",
            model="Latitude",
            serial_number="EQ-IN-001",
            status=EquipmentStatus.OK,
            room=cls.room,
        )

        cls.outside_scope_equipment = Equipment.objects.create(
            name="Outside Scope Laptop",
            brand="HP",
            model="EliteBook",
            serial_number="EQ-OUT-001",
            status=EquipmentStatus.OK,
            room=cls.other_room,
        )

        # -------------------------
        # Users
        # -------------------------

        cls.user = User.objects.create_user(
            email="roomadmin@example.com",
            password="password",
        )

        cls.role = RoleAssignment.objects.create(
            user=cls.user,
            role="ROOM_ADMIN",
            room=cls.room,
        )

        cls.user.active_role = cls.role
        cls.user.save()

        cls.no_permission_user = User.objects.create_user(
            email="noperms@example.com",
            password="password",
        )

        cls.no_permission_role = RoleAssignment.objects.create(
            user=cls.no_permission_user,
            role="ROOM_ADMIN",
            room=cls.room,
        )

        cls.no_permission_user.active_role = cls.no_permission_role
        cls.no_permission_user.save()

        # -------------------------
        # URLs
        # -------------------------

        cls.list_url = reverse("equipments")
        cls.in_scope_detail_url = reverse(
            "equipment-detail",
            kwargs={
                "public_id": cls.in_scope_equipment.public_id,
            },
        )
        cls.outside_scope_detail_url = reverse(
            "equipment-detail",
            kwargs={
                "public_id": cls.outside_scope_equipment.public_id,
            },
        )

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------

    @classmethod
    def grant_permission(cls, role, permission_code):
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

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    def test_anonymous_user_cannot_list_equipment(self):
        response = self.client.get(
            self.list_url,
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_user_without_assets_view_cannot_list_equipment(self):
        self.authenticate(
            self.no_permission_user,
        )

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_user_with_assets_view_can_list_in_scope_equipment(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "assets.view",
        )
        self.authenticate(
            self.user,
        )

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.data

        if isinstance(data, dict) and "results" in data:
            rows = data["results"]
        else:
            rows = data

        public_ids = {
            row["public_id"]
            for row in rows
        }

        self.assertIn(
            self.in_scope_equipment.public_id,
            public_ids,
        )
        self.assertNotIn(
            self.outside_scope_equipment.public_id,
            public_ids,
        )

    def test_user_with_assets_view_can_retrieve_in_scope_equipment(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "assets.view",
        )
        self.authenticate(
            self.user,
        )

        response = self.client.get(
            self.in_scope_detail_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["public_id"],
            self.in_scope_equipment.public_id,
        )

    def test_user_with_assets_view_cannot_retrieve_outside_scope_equipment(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "assets.view",
        )
        self.authenticate(
            self.user,
        )

        response = self.client.get(
            self.outside_scope_detail_url,
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ],
        )

    # ------------------------------------------------------------------
    # Create access
    # ------------------------------------------------------------------

    def test_user_without_assets_create_cannot_create_equipment(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "assets.view",
        )
        self.authenticate(
            self.user,
        )

        payload = {
            "name": "New Laptop",
            "brand": "Lenovo",
            "model": "ThinkPad",
            "serial_number": "EQ-NEW-001",
            "status": EquipmentStatus.OK,
            "room": self.room.public_id,
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_user_with_assets_create_can_create_equipment_in_scope(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "assets.create",
        )
        self.authenticate(
            self.user,
        )

        payload = {
            "name": "Created Laptop",
            "brand": "Lenovo",
            "model": "ThinkPad",
            "serial_number": "EQ-CREATED-001",
            "status": EquipmentStatus.OK,
            "room": self.room.public_id,
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Equipment.objects.filter(
                serial_number="EQ-CREATED-001",
                room=self.room,
            ).exists()
        )

    def test_user_with_assets_create_cannot_create_equipment_outside_scope(self):
        self.grant_permission(
            "ROOM_ADMIN",
            "assets.create",
        )
        self.authenticate(
            self.user,
        )

        payload = {
            "name": "Outside Laptop",
            "brand": "Lenovo",
            "model": "ThinkPad",
            "serial_number": "EQ-CREATED-OUT-001",
            "status": EquipmentStatus.OK,
            "room": self.other_room.public_id,
        }

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
            ],
        )

        self.assertFalse(
            Equipment.objects.filter(
                serial_number="EQ-CREATED-OUT-001",
            ).exists()
        )