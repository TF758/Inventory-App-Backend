from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from db_inventory.permissions.helpers import is_in_scope, check_permission, ensure_permission
from db_inventory.factories import UserFactory, RoomFactory, LocationFactory, DepartmentFactory, AdminUserFactory
from db_inventory.models import User, Room, Location, Department, RoleAssignment
from rest_framework.exceptions import PermissionDenied
from django.urls import reverse


class LocationAdminScopeTests(TestCase):
    """
    Test Location-level role permissions:
      - LocationAdmin and LocationViewer roles
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




    def test_location_admin_access_own_location(self):
        """LocationAdmin can access their assigned location"""
        role = RoleAssignment.objects.create(user=self.user, role="LOCATION_ADMIN", location=self.loc1)
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "LOCATION_VIEWER", location=self.loc1))
        self.assertTrue(is_in_scope(role, location=self.loc1))

    def test_location_admin_access_own_rooms(self):
        """LocationAdmin can access rooms under their location"""
        role = RoleAssignment.objects.create(user=self.user, role="LOCATION_ADMIN", location=self.loc1)
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(role, room=self.room1))

    def test_location_admin_cannot_access_other_location(self):
        """LocationAdmin cannot access locations outside their scope"""
        role = RoleAssignment.objects.create(user=self.user, role="LOCATION_ADMIN", location=self.loc1)
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "LOCATION_VIEWER", location=self.loc2))
        self.assertFalse(is_in_scope(role, location=self.loc2))

    def test_location_admin_cannot_access_rooms_outside_scope(self):
        """LocationAdmin cannot access rooms outside their assigned location"""
        role = RoleAssignment.objects.create(user=self.user, role="LOCATION_ADMIN", location=self.loc1)
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.room2))
        self.assertFalse(is_in_scope(role, room=self.room2))

   
    def test_site_admin_bypass_location_scope(self):
        """SITE_ADMIN can access any location or room regardless of assignment"""
        self.assertTrue(check_permission(self.admin_user, "LOCATION_ADMIN", location=self.loc1))
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room2))
        self.assertTrue(is_in_scope(self.site_admin_role, location=self.loc2))
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room1))

    def test_missing_active_role_denied(self):
        """User without an active role cannot access locations or rooms"""
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))

    def test_ensure_permission_raises_for_out_of_scope(self):
        """ensure_permission should raise PermissionDenied if access is out of scope"""
        role = RoleAssignment.objects.create(user=self.user, role="LOCATION_ADMIN", location=self.loc1)
        self.user.active_role = role
        self.user.save()


        with self.assertRaises(PermissionDenied):
            ensure_permission(self.user, "ROOM_ADMIN", room=self.room2)



class LocationViewerTests(TestCase):
    """
    Tests for LocationViewer role:
      - Can view locations and rooms within their assigned scope
      - Cannot create, update, or delete (CRUD) locations or rooms
      - Enforces read-only permissions correctly
    """

    def setUp(self):
        # Departments
        self.dept1 = DepartmentFactory(name="Chemistry")

        # Location & Room
        self.loc1 = LocationFactory(name="Building A", department=self.dept1)
        self.room1 = RoomFactory(name="Lab 101", location=self.loc1)

        # User and role
        self.user = UserFactory()
        self.role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_VIEWER",
            location=self.loc1
        )
        self.user.active_role = self.role
        self.user.save()

    def test_location_viewer_can_view_location(self):
        """LocationViewer can view their assigned location"""
        self.assertTrue(check_permission(self.user, "LOCATION_VIEWER", location=self.loc1))
        self.assertTrue(is_in_scope(self.role, location=self.loc1))

    def test_location_viewer_cannot_create_location(self):
        """LocationViewer cannot create a new location"""
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))

    def test_location_viewer_cannot_update_location(self):
        """LocationViewer cannot update their assigned location"""
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))

    def test_location_viewer_cannot_delete_location(self):
        """LocationViewer cannot delete their assigned location"""
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))

    def test_location_viewer_can_view_rooms_in_scope(self):
        """LocationViewer can view rooms under their assigned location"""
        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(self.role, room=self.room1))

    def test_location_viewer_cannot_create_update_delete_room(self):
        """LocationViewer cannot perform admin actions on rooms in their location"""
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))
        self.assertFalse(check_permission(self.user, "ROOM_CLERK", room=self.room1)) 


class LocationPermissionAPITests(APITestCase):
    """
    API-level enforcement tests for LocationPermission:
      - Ensures method_role_map is respected
      - Validates end-to-end permission behavior for different roles
    """

    def setUp(self):
        self.client = APIClient()

        self.dept = DepartmentFactory(name="Physics")
        self.loc = LocationFactory(name="Building A", department=self.dept)
        self.room = RoomFactory(name="Lab 101", location=self.loc)

        self.viewer = UserFactory()
        self.admin = UserFactory()
        self.site_admin = AdminUserFactory()
        self.dep_admin = UserFactory()

        # Assign roles
        self.viewer_role = RoleAssignment.objects.create(user=self.viewer, role="LOCATION_VIEWER", location=self.loc)
        self.viewer.active_role = self.viewer_role
        self.viewer.save()

        self.admin_role = RoleAssignment.objects.create(user=self.admin, role="LOCATION_ADMIN", location=self.loc)
        self.admin.active_role = self.admin_role
        self.admin.save()

        self.site_admin_role = RoleAssignment.objects.create(user=self.site_admin, role="SITE_ADMIN")
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

        self.dep_role =  RoleAssignment.objects.create(user=self.dep_admin, role="DEPARTMENT_ADMIN", department=self.dept)
        self.dep_admin.active_role = self.dep_role
        self.dep_admin.save()

        self.url = reverse("location-detail", args=[self.loc.public_id])

    # --- VIEWER TESTS ---
    def test_location_viewer_can_get(self):
        """LocationViewer can GET their location"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_location_viewer_cannot_post(self):
        """LocationViewer cannot POST a new location"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(reverse("locations"), {"name": "Building B"})
        self.assertIn(response.status_code, [403, 405]) 

    def test_location_viewer_cannot_patch(self):
        """LocationViewer cannot PATCH"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.patch(self.url, {"name": "New Name"})
        self.assertEqual(response.status_code, 403)

    def test_location_viewer_cannot_delete(self):
        """LocationViewer cannot DELETE"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 403)

    # --- ADMIN TESTS ---
    def test_location_admin_can_edit(self):
        """LocationAdmin can EDIT their own location"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.put(self.url, {"name": "Updated Building", "department": self.dept.public_id })
        self.assertIn(response.status_code, [200, 204])

    def test_location_admin_can_get(self):
        """LocationAdmin can GET their own location"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_location_admin_cannot_post(self):
        """LocationAdmin cannot create a location"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(reverse("locations"), {"name": "New Building"})
        self.assertIn(response.status_code, [403, 405]) 

    
    def test_location_admin_cannot_delete(self):
        """LocationAdmin cannot DELETE any location"""
        self.client.force_authenticate(user=self.viewer)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 403)


    def test_location_admin_cannot_delete_outside_scope(self):
        """LocationAdmin cannot DELETE areas they don't control"""
        loc2 = LocationFactory(name="Other Building")
        room2 = RoomFactory(name = "Marvin's Room", location = loc2)
        loc_url = reverse("location-detail", args=[loc2.public_id])
        room_url = reverse("room-detail", args=[room2.public_id])
        self.client.force_authenticate(user=self.admin)
        loc_response = self.client.delete(loc_url)
        room_response = self.client.delete(room_url)
        self.assertEqual(loc_response.status_code, 403)
        self.assertEqual(room_response.status_code, 403)

    # --- SITE ADMIN TESTS ---
    def test_dep_admin_supercede_location_level(self):
        """SITE_ADMIN by passes all permission for location objects"""
        loc2 = LocationFactory(name="Other Building")
        dep2 = DepartmentFactory(name = "My Department")
        url2 = reverse("location-detail", args=[loc2.public_id])
        self.client.force_authenticate(user=self.site_admin)
        get_response = self.client.get(url2)
        post_response = self.client.post(
        reverse("locations"),
        {"name": "Site Admin Made This", "department": str(dep2.public_id)},)
        put_response = self.client.put(url2,{
                "name": "Site Admin Updated Name",
                "department": str(dep2.public_id),})
        del_response =  self.client.delete(url2)
        self.assertIn(del_response.status_code, [204, 200])
        self.assertIn(put_response.status_code, [204, 200])
        self.assertIn(get_response.status_code, [204, 200])
        self.assertIn(post_response.status_code, [200, 201, 204])

    def test_dep_admin_supercede_location_level(self):
        """DEPARTMENT ADMIN can perform all operations within their department"""

        # Make the location belong to the DEPARTMENT_ADMIN's department
        test_loc = LocationFactory(
            name="Dep Admin Location", 
            department=self.dep_admin.active_role.department
        )

        url = reverse("location-detail", args=[test_loc.public_id])
        self.client.force_authenticate(user=self.dep_admin)

        # --- GET ---
        get_response = self.client.get(url)

        # --- POST ---
        post_response = self.client.post(
            reverse("locations"),
            {
                "name": "Dep Admin Made This",
                "department": str(self.dep_admin.active_role.department.public_id),
            }
        )

        # --- PUT ---
        put_response = self.client.put(
            url,
            {
                "name": "Dep Admin Updated Location",
                "department": str(self.dep_admin.active_role.department.public_id),
            }
        )

        # --- DELETE ---
        del_response = self.client.delete(url)

        # --- Assertions ---
        self.assertIn(get_response.status_code, [200, 204])
        self.assertIn(post_response.status_code, [200, 201, 204])
        self.assertIn(put_response.status_code, [200, 204])
        self.assertIn(del_response.status_code, [200, 204])

    def test_dep_admin_cannot_access_location_outside_department(self):
        """DEPARTMENT_ADMIN cannot access locations outside their assigned department"""

        # Create a location in a different department
        other_dep = DepartmentFactory(name="Other Department")
        other_loc = LocationFactory(name="Other Location", department=other_dep)
        other_url = reverse("location-detail", args=[other_loc.public_id])

        self.client.force_authenticate(user=self.dep_admin)

        get_response = self.client.get(other_url)
        post_response = self.client.post(
            reverse("locations"),
            {"name": "Invalid Creation", "department": str(other_dep.public_id)}
        )
        put_response = self.client.put(
            other_url,
            {"name": "Invalid Update", "department": str(other_dep.public_id)}
        )
        delete_response = self.client.delete(other_url)

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.assertEqual(put_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        

