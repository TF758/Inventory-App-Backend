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
      - Ensures method_role_map is respected
      - Validates end-to-end permission behavior for ROOM_VIEWER, ROOM_ADMIN, LOCATION_ADMIN, SITE_ADMIN
      - Scope enforcement at department/location/room level
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
        self.admin = UserFactory()
        self.site_admin = AdminUserFactory()
        self.loc_admin = UserFactory()
        self.dep_admin = UserFactory()

        # Assign roles
        self.viewer_role = RoleAssignment.objects.create(user=self.viewer, role="ROOM_VIEWER", room=self.room)
        self.viewer.active_role = self.viewer_role
        self.viewer.save()

        self.admin_role = RoleAssignment.objects.create(user=self.admin, role="ROOM_ADMIN", room=self.room)
        self.admin.active_role = self.admin_role
        self.admin.save()

        self.loc_admin_role = RoleAssignment.objects.create(user=self.loc_admin, role="LOCATION_ADMIN", location=self.loc)
        self.loc_admin.active_role = self.loc_admin_role
        self.loc_admin.save()

        self.site_admin_role = RoleAssignment.objects.create(user=self.site_admin, role="SITE_ADMIN")
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

        self.dep_role = RoleAssignment.objects.create(user=self.dep_admin, role="DEPARTMENT_ADMIN", department=self.dept)
        self.dep_admin.active_role = self.dep_role
        self.dep_admin.save()

        # Test URLs
        self.get_url = reverse("room-detail", args=[self.room.public_id])
        self.put_url = reverse("room-detail", args=[self.room.public_id])
        self.patch_url = reverse("room-detail", args=[self.room.public_id])
        self.delete_url = reverse("room-detail", args=[self.room.public_id])
        self.post_url = reverse("rooms")  # list/create endpoint
        self.other_get_url = reverse("room-detail", args=[self.other_room.public_id])
        self.other_put_url = reverse("room-detail", args=[self.other_room.public_id])
        self.other_delete_url = reverse("room-detail", args=[self.other_room.public_id])

    # --- ROOM_VIEWER TESTS ---
    def test_room_viewer_can_get(self):
        """ROOM_VIEWER can GET their room"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(self.get_url)
        self.assertEqual(response.status_code, 200)

    def test_room_viewer_cannot_post_patch_delete(self):
        """ROOM_VIEWER cannot modify rooms"""
        self.client.force_authenticate(user=self.viewer)

        post_response = self.client.post(self.post_url, {"name": "Test Room", "location": self.loc.public_id})
        self.assertIn(post_response.status_code, [403, 405])

        put_response = self.client.put(self.put_url, {"name": "Updated Room", "location": self.loc.public_id})
        self.assertEqual(put_response.status_code, 403)

        patch_response = self.client.patch(self.patch_url, {"name": "Patched Room", "location": self.loc.public_id})
        self.assertEqual(patch_response.status_code, 403)

        delete_response = self.client.delete(self.delete_url)
        self.assertEqual(delete_response.status_code, 403)

    # --- ROOM_ADMIN TESTS ---
    def test_room_admin_can_edit_own_room(self):
        """ROOM_ADMIN can PUT/PATCH their room"""
        self.client.force_authenticate(user=self.admin)

        put_response = self.client.put(self.put_url, {"name": "Updated Room", "location": self.loc.public_id})
        self.assertIn(put_response.status_code, [200, 204])

        patch_response = self.client.patch(self.patch_url, {"name": "Patched Room", "location": self.loc.public_id})
        self.assertIn(patch_response.status_code, [200, 204])

    def test_room_admin_cannot_edit_outside_scope(self):
        """ROOM_ADMIN cannot modify rooms outside their location"""
        self.client.force_authenticate(user=self.admin)

        put_response = self.client.put(self.other_put_url, {"name": "Invalid Update", "location": self.other_room.location.public_id})
        self.assertEqual(put_response.status_code, 403)

        delete_response = self.client.delete(self.other_delete_url)
        self.assertEqual(delete_response.status_code, 403)

    def test_room_admin_cannot_create_rooms(self):
        """ROOM_ADMIN cannot create rooms (restricted by design)"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.post_url, {"name": "New Room", "location": self.loc.public_id})
        self.assertEqual(response.status_code, 403)

    # --- SITE_ADMIN TESTS ---
    def test_site_admin_can_manage_any_room(self):
        """SITE_ADMIN can GET, POST, PUT, DELETE any room"""
        self.client.force_authenticate(user=self.site_admin)

        get_response = self.client.get(self.get_url)
        self.assertIn(get_response.status_code, [200, 204])

        post_response = self.client.post(self.post_url, {"name": "New Room", "location": self.loc.public_id})
        self.assertIn(post_response.status_code, [200, 201, 204])

        put_response = self.client.put(self.put_url, {"name": "Updated Room", "location": self.loc.public_id})
        self.assertIn(put_response.status_code, [200, 204])

        delete_response = self.client.delete(self.delete_url)
        self.assertIn(delete_response.status_code, [200, 204])

    # --- DEPARTMENT_ADMIN TESTS ---
    def test_dep_admin_can_manage_rooms_within_department(self):
        """DEPARTMENT_ADMIN can manage rooms within their department"""
        room_in_dep = RoomFactory(name="Dep Room", location=self.loc)
        self.client.force_authenticate(user=self.dep_admin)

        get_response = self.client.get(reverse("room-detail", args=[room_in_dep.public_id]))
        self.assertIn(get_response.status_code, [200, 204])

        post_response = self.client.post(self.post_url, {"name": "New Dep Room", "location": self.loc.public_id})
        self.assertIn(post_response.status_code, [200, 201, 204])

        put_response = self.client.put(reverse("room-detail", args=[room_in_dep.public_id]), {"name": "Updated Dep Room", "location": self.loc.public_id})
        self.assertIn(put_response.status_code, [200, 204])

        delete_response = self.client.delete(reverse("room-detail", args=[room_in_dep.public_id]))
        self.assertIn(delete_response.status_code, [200, 204])

    def test_dep_admin_cannot_access_rooms_outside_department(self):
        """DEPARTMENT_ADMIN cannot access rooms outside their department"""
        self.client.force_authenticate(user=self.dep_admin)

        # GET
        get_response = self.client.get(self.other_get_url)
        self.assertEqual(get_response.status_code, 403)

        # POST
        post_response = self.client.post(self.post_url, {"name": "Invalid Room", "location": self.other_room.location.public_id})
        self.assertEqual(post_response.status_code, 403)

        # PUT
        put_response = self.client.put(self.other_put_url, {"name": "Invalid Update", "location": self.other_room.location.public_id})
        self.assertEqual(put_response.status_code, 403)

        # DELETE
        delete_response = self.client.delete(self.other_delete_url)
        self.assertEqual(delete_response.status_code, 403)

    # --- LOCATION_ADMIN TESTS ---
    def test_location_admin_can_manage_rooms_in_location(self):
        """LOCATION_ADMIN can manage rooms in their assigned location"""
        self.client.force_authenticate(user=self.loc_admin)

        # GET
        get_response = self.client.get(self.get_url)
        self.assertIn(get_response.status_code, [200, 204], "LOCATION_ADMIN should be able to GET rooms in their location")

        # POST
        post_response = self.client.post(self.post_url, {"name": "New Room", "location": self.loc.public_id})
        self.assertIn(post_response.status_code, [200, 201, 204], "LOCATION_ADMIN should be able to POST rooms in their location")

        # PUT
        put_response = self.client.put(self.put_url, {"name": "Updated Room", "location": self.loc.public_id})
        self.assertIn(put_response.status_code, [200, 204], "LOCATION_ADMIN should be able to PUT rooms in their location")

        # PATCH
        patch_response = self.client.patch(self.patch_url, {"name": "Patched Room", "location": self.loc.public_id})
        self.assertIn(patch_response.status_code, [200, 204], "LOCATION_ADMIN should be able to PATCH rooms in their location")

        # DELETE
        delete_response = self.client.delete(self.delete_url)
        self.assertIn(delete_response.status_code, [200, 204], "LOCATION_ADMIN should be able to DELETE rooms in their location")


    def test_location_admin_cannot_manage_rooms_outside_location(self):
        """LOCATION_ADMIN cannot manage rooms outside their assigned location"""
        self.client.force_authenticate(user=self.loc_admin)

        # GET outside location
        get_response = self.client.get(self.other_get_url)
        self.assertEqual(get_response.status_code, 403, "LOCATION_ADMIN should not be able to GET rooms outside their location")

        # POST outside location
        post_response = self.client.post(self.post_url, {"name": "Invalid Room", "location": self.other_room.location.public_id})
        self.assertEqual(post_response.status_code, 403, "LOCATION_ADMIN should not be able to POST rooms outside their location")

        # PUT outside location
        put_response = self.client.put(self.other_put_url, {"name": "Invalid Update", "location": self.other_room.location.public_id})
        self.assertEqual(put_response.status_code, 403, "LOCATION_ADMIN should not be able to PUT rooms outside their location")

        # PATCH outside location
        patch_response = self.client.patch(self.other_put_url, {"name": "Invalid Patch", "location": self.other_room.location.public_id})
        self.assertEqual(patch_response.status_code, 403, "LOCATION_ADMIN should not be able to PATCH rooms outside their location")

        # DELETE outside location
        delete_response = self.client.delete(self.other_delete_url)
        self.assertEqual(delete_response.status_code, 403, "LOCATION_ADMIN should not be able to DELETE rooms outside their location")