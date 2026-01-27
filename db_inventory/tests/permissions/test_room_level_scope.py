from rest_framework.test import APIClient, APITestCase
from db_inventory.factories import UserFactory, RoomFactory, LocationFactory, DepartmentFactory, AdminUserFactory
from django.urls import reverse
from db_inventory.models import User, Room, Location, Department, RoleAssignment
from db_inventory.permissions.helpers import is_in_scope, check_permission, ensure_permission
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
class RoomAdminScopeTests(TestCase):
    """
    Test Room-level role permissions:
      - ROOM_ADMIN and ROOM_VIEWER roles
      - Hierarchy and scope enforcement
      - SITE_ADMIN bypass
    """

    @classmethod
    def setUpTestData(cls):
        # Departments
        cls.dept1 = DepartmentFactory(name="Chemistry")
        cls.dept2 = DepartmentFactory(name="Biology")

        # Locations
        cls.loc1 = LocationFactory(name="Building A", department=cls.dept1)
        cls.loc2 = LocationFactory(name="Building B", department=cls.dept2)

        # Rooms
        cls.room1 = RoomFactory(name="Lab 101", location=cls.loc1)
        cls.room2 = RoomFactory(name="Lab 202", location=cls.loc2)

        # Users
        cls.user = UserFactory()
        cls.admin_user = AdminUserFactory()

        # Site admin role
        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.admin_user,
            role="SITE_ADMIN",
        )
        cls.admin_user.active_role = cls.site_admin_role
        cls.admin_user.save()

    # --- ROOM_ADMIN tests ---
    def test_room_admin_access_own_room(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(role, room=self.room1))

    def test_room_admin_cannot_access_other_room(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.room2))
        self.assertFalse(is_in_scope(role, room=self.room2))

    def test_site_admin_bypass_room_scope(self):
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room1))
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room2))
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room1))
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room2))

    def test_missing_active_role_denied_room(self):
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))

    def test_ensure_permission_raises_for_out_of_scope_room(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room1,
        )
        self.user.active_role = role
        self.user.save()

        with self.assertRaises(PermissionDenied):
            ensure_permission(self.user, "ROOM_ADMIN", room=self.room2)

    # --- ROOM_VIEWER tests ---
    def test_room_viewer_can_view_own_room(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_VIEWER",
            room=self.room1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(role, room=self.room1))

    def test_room_viewer_cannot_modify_room(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_VIEWER",
            room=self.room1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room2))

class RoomPermissionAPITests(APITestCase):
    """
    API-level enforcement tests for RoomPermission.
    """

    @classmethod
    def setUpTestData(cls):
        # Departments & Locations
        cls.dept = DepartmentFactory(name="Physics")
        cls.other_dept = DepartmentFactory(name="Other Dept")

        cls.loc = LocationFactory(name="Building A", department=cls.dept)
        cls.other_loc = LocationFactory(name="Other Building", department=cls.other_dept)

        # Rooms
        cls.room = RoomFactory(name="Lab 101", location=cls.loc)
        cls.other_room = RoomFactory(name="Lab 202", location=cls.other_loc)

        # Users
        cls.viewer = UserFactory()
        cls.room_admin = UserFactory()
        cls.loc_admin = UserFactory()
        cls.dep_admin = UserFactory()
        cls.site_admin = AdminUserFactory()

        # Roles
        cls.viewer.active_role = RoleAssignment.objects.create(
            user=cls.viewer,
            role="ROOM_VIEWER",
            room=cls.room,
        )
        cls.room_admin.active_role = RoleAssignment.objects.create(
            user=cls.room_admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.loc_admin.active_role = RoleAssignment.objects.create(
            user=cls.loc_admin,
            role="LOCATION_ADMIN",
            location=cls.loc,
        )
        cls.dep_admin.active_role = RoleAssignment.objects.create(
            user=cls.dep_admin,
            role="DEPARTMENT_ADMIN",
            department=cls.dept,
        )
        cls.site_admin.active_role = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )

        for u in (cls.viewer, cls.room_admin, cls.loc_admin, cls.dep_admin, cls.site_admin):
            u.save()

        cls.detail_url = reverse("room-detail", args=[cls.room.public_id])
        cls.other_detail_url = reverse("room-detail", args=[cls.other_room.public_id])
        cls.list_url = reverse("rooms")

    def setUp(self):
        self.client = APIClient()
    # ---------------- VIEWER ----------------

    def test_room_viewer_can_get(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)

    def test_room_viewer_cannot_modify(self):
        self.client.force_authenticate(self.viewer)

        self.assertEqual(self.client.put(self.detail_url, {"name": "X"}).status_code, 403)
        self.assertEqual(self.client.patch(self.detail_url, {"name": "X"}).status_code, 403)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)

    # ---------------- ROOM ADMIN ----------------

    def test_room_admin_can_update_name_only(self):
        self.client.force_authenticate(self.room_admin)

        self.assertIn(self.client.patch(self.detail_url, {"name": "Updated"}).status_code,[200, 204],)

        self.assertIn(
            self.client.patch(self.detail_url, {"name": "Patched"}).status_code,
            [200, 204],
        )

    def test_room_admin_cannot_change_location(self):
        self.client.force_authenticate(self.room_admin)

        response = self.client.patch(
            self.detail_url,
            {"location": self.other_loc.public_id}
        )
        self.assertEqual(response.status_code, 403)

    def test_room_admin_cannot_access_other_room(self):
        self.client.force_authenticate(self.room_admin)
        self.assertEqual(self.client.get(self.other_detail_url).status_code, 403)

    def test_room_admin_cannot_create_rooms(self):
        self.client.force_authenticate(self.room_admin)
        self.assertEqual(
            self.client.post(self.list_url, {"name": "New", "location": self.loc.public_id}).status_code,
            403,
        )

    # ---------------- LOCATION ADMIN ----------------

    def test_location_admin_can_manage_rooms_in_location(self):
        self.client.force_authenticate(self.loc_admin)

        self.assertEqual(self.client.get(self.detail_url).status_code, 200)
        self.assertIn(
            self.client.post(self.list_url, {"name": "New", "location": self.loc.public_id}).status_code,
            [200, 201],
        )
        self.assertIn(self.client.patch(self.detail_url, {"name": "Updated"}).status_code,[200, 204],)

        self.assertIn(
            self.client.patch(self.detail_url, {"name": "Patched"}).status_code,
            [200, 204],
        )
        self.assertIn(
            self.client.delete(self.detail_url).status_code,
            [200, 204],
        )

    def test_location_admin_cannot_change_room_location(self):
        self.client.force_authenticate(self.loc_admin)

        response = self.client.patch(
            self.detail_url,
            {"location": self.other_loc.public_id}
        )
        self.assertEqual(response.status_code, 403)

    def test_location_admin_cannot_access_other_location(self):
        self.client.force_authenticate(self.loc_admin)
        self.assertEqual(self.client.get(self.other_detail_url).status_code, 403)

    # ---------------- DEPARTMENT ADMIN ----------------

    def test_department_admin_can_reassign_room_location_within_department(self):
        new_loc = LocationFactory(department=self.dept)

        self.client.force_authenticate(self.dep_admin)
        response = self.client.patch(
            self.detail_url,
            {"location": new_loc.public_id}
        )

        self.assertIn(response.status_code, [200, 204])

    def test_department_admin_cannot_access_other_department(self):
        self.client.force_authenticate(self.dep_admin)
        self.assertEqual(self.client.get(self.other_detail_url).status_code, 403)

    # ---------------- SITE ADMIN ----------------

    def test_site_admin_can_manage_any_room(self):
        self.client.force_authenticate(self.site_admin)

        self.assertEqual(self.client.get(self.detail_url).status_code, 200)
        self.assertIn(
            self.client.post(self.list_url, {"name": "X", "location": self.loc.public_id}).status_code,
            [200, 201],
        )
        self.assertIn(
            self.client.patch(self.detail_url, {"location": self.other_loc.public_id}).status_code,
            [200, 204],
        )
        self.assertIn(
            self.client.delete(self.detail_url).status_code,
            [200, 204],
        )
