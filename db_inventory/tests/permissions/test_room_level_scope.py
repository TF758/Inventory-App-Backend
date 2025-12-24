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

    def setUp(self):
        # Departments
        self.dept1 = DepartmentFactory(name="Chemistry")
        self.dept2 = DepartmentFactory(name="Biology")

        # Locations
        self.loc1 = LocationFactory(name="Building A", department=self.dept1)
        self.loc2 = LocationFactory(name="Building B", department=self.dept2)

        # Rooms
        self.room1 = RoomFactory(name="Lab 101", location=self.loc1)
        self.room2 = RoomFactory(name="Lab 202", location=self.loc2)

        # Users
        self.user = UserFactory()
        self.admin_user = AdminUserFactory()

        # Site admin role
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.admin_user, role="SITE_ADMIN"
        )
        self.admin_user.active_role = self.site_admin_role
        self.site_admin_role.save()

    # --- ROOM_ADMIN tests ---
    def test_room_admin_access_own_room(self):
        """ROOM_ADMIN can access their assigned room"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_ADMIN", room=self.room1)
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(role, room=self.room1))

    def test_room_admin_cannot_access_other_room(self):
        """ROOM_ADMIN cannot access rooms outside their location"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_ADMIN",  room=self.room1)
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.room2))
        self.assertFalse(is_in_scope(role, room=self.room2))

    def test_site_admin_bypass_room_scope(self):
        """SITE_ADMIN can access any room"""
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room1))
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room2))
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room1))
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room2))

    def test_missing_active_role_denied_room(self):
        """User without active role cannot access rooms"""
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))

    def test_ensure_permission_raises_for_out_of_scope_room(self):
        """ensure_permission should raise PermissionDenied if room out of scope"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_ADMIN",  room=self.room1)
        self.user.active_role = role
        self.user.save()

        with self.assertRaises(PermissionDenied):
            ensure_permission(self.user, "ROOM_ADMIN", room=self.room2)


    # --- ROOM_VIEWER tests ---
    def test_room_viewer_can_view_own_room(self):
        """ROOM_VIEWER can view rooms within their location"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_VIEWER",  room=self.room1)
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(role, room=self.room1))

    def test_room_viewer_cannot_modify_room(self):
        """ROOM_VIEWER cannot POST/PUT/PATCH/DELETE rooms"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_VIEWER", room=self.room1)
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room2))

class RoomPermissionAPITests(APITestCase):
    """
    API-level enforcement tests for RoomPermission:
    Enforces field-level business rules:
      - Name changes vs location reassignment
      - Scope enforcement
      - Role hierarchy
    """

    def setUp(self):
        self.client = APIClient()

        # Departments & Locations
        self.dept = DepartmentFactory(name="Physics")
        self.other_dept = DepartmentFactory(name="Other Dept")

        self.loc = LocationFactory(name="Building A", department=self.dept)
        self.other_loc = LocationFactory(name="Other Building", department=self.other_dept)

        # Rooms
        self.room = RoomFactory(name="Lab 101", location=self.loc)
        self.other_room = RoomFactory(name="Lab 202", location=self.other_loc)

        # Users
        self.viewer = UserFactory()
        self.room_admin = UserFactory()
        self.loc_admin = UserFactory()
        self.dep_admin = UserFactory()
        self.site_admin = AdminUserFactory()

        # Roles
        self.viewer.active_role = RoleAssignment.objects.create(
            user=self.viewer, role="ROOM_VIEWER", room=self.room
        )
        self.room_admin.active_role = RoleAssignment.objects.create(
            user=self.room_admin, role="ROOM_ADMIN", room=self.room
        )
        self.loc_admin.active_role = RoleAssignment.objects.create(
            user=self.loc_admin, role="LOCATION_ADMIN", location=self.loc
        )
        self.dep_admin.active_role = RoleAssignment.objects.create(
            user=self.dep_admin, role="DEPARTMENT_ADMIN", department=self.dept
        )
        self.site_admin.active_role = RoleAssignment.objects.create(
            user=self.site_admin, role="SITE_ADMIN"
        )

        for u in [self.viewer, self.room_admin, self.loc_admin, self.dep_admin, self.site_admin]:
            u.save()

        # URLs
        self.detail_url = reverse("room-detail", args=[self.room.public_id])
        self.other_detail_url = reverse("room-detail", args=[self.other_room.public_id])
        self.list_url = reverse("rooms")

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
