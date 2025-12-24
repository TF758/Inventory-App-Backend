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
    API-level enforcement tests for LocationPermission.
    Enforces:
      - Scope limits
      - Field-level restrictions (department reassignment)
      - Role hierarchy
    """

    def setUp(self):
        self.client = APIClient()

        self.dept = DepartmentFactory(name="Physics")
        self.other_dept = DepartmentFactory(name="Other Dept")

        self.loc = LocationFactory(name="Building A", department=self.dept)
        self.other_loc = LocationFactory(name="Building B", department=self.other_dept)

        self.viewer = UserFactory()
        self.loc_admin = UserFactory()
        self.dep_admin = UserFactory()
        self.site_admin = AdminUserFactory()

        # Roles
        self.viewer.active_role = RoleAssignment.objects.create(
            user=self.viewer, role="LOCATION_VIEWER", location=self.loc
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

        for u in [self.viewer, self.loc_admin, self.dep_admin, self.site_admin]:
            u.save()

        self.url = reverse("location-detail", args=[self.loc.public_id])
        self.other_url = reverse("location-detail", args=[self.other_loc.public_id])

    # ---------------- VIEWER ----------------

    def test_location_viewer_can_get(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_location_viewer_cannot_modify(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.patch(self.url, {"name": "X"}).status_code, 403)
        self.assertEqual(self.client.delete(self.url).status_code, 403)

    # ---------------- LOCATION ADMIN ----------------

    def test_location_admin_can_edit_name_only(self):
        """LOCATION_ADMIN can change name but not department"""
        self.client.force_authenticate(self.loc_admin)
        response = self.client.patch(self.url, {"name": "Updated Building"})
        self.assertIn(response.status_code, [200, 204])

    def test_location_admin_cannot_change_department(self):
        """LOCATION_ADMIN cannot reassign department"""
        self.client.force_authenticate(self.loc_admin)
        response = self.client.patch(
            self.url,
            {"department": str(self.other_dept.public_id)}
        )
        self.assertEqual(response.status_code, 403)

    def test_location_admin_cannot_access_outside_scope(self):
        self.client.force_authenticate(self.loc_admin)
        self.assertEqual(self.client.get(self.other_url).status_code, 403)

    # ---------------- DEPARTMENT ADMIN ----------------

    def test_department_admin_can_manage_locations_in_department(self):
        """DEPARTMENT_ADMIN can manage locations except department reassignment"""

        test_loc = LocationFactory(
            name="Dep Location",
            department=self.dept
        )
        url = reverse("location-detail", args=[test_loc.public_id])

        self.client.force_authenticate(self.dep_admin)

        # GET
        self.assertIn(self.client.get(url).status_code, [200, 204])

        # POST
        self.assertIn(
            self.client.post(
                reverse("locations"),
                {
                    "name": "Dep Created",
                    "department": str(self.dept.public_id),
                }
            ).status_code,
            [200, 201, 204],
        )

        # PATCH name
        self.assertIn(
            self.client.patch(
                url,
                {"name": "Updated by Dep Admin"}
            ).status_code,
            [200, 204],
        )

        # DELETE
        self.assertIn(self.client.delete(url).status_code, [200, 204])

    def test_department_admin_cannot_change_department(self):
        """DEPARTMENT_ADMIN cannot reassign location department"""
        test_loc = LocationFactory(department=self.dept)
        url = reverse("location-detail", args=[test_loc.public_id])

        self.client.force_authenticate(self.dep_admin)

        response = self.client.patch(
            url,
            {"department": str(self.other_dept.public_id)}
        )
        self.assertEqual(response.status_code, 403)

    def test_department_admin_cannot_access_other_department(self):
        self.client.force_authenticate(self.dep_admin)
        self.assertEqual(self.client.get(self.other_url).status_code, 403)

    # ---------------- SITE ADMIN ----------------

    def test_site_admin_can_manage_any_location(self):
        """SITE_ADMIN bypasses all scope and field restrictions"""

        self.client.force_authenticate(self.site_admin)

        self.assertIn(self.client.get(self.other_url).status_code, [200, 204])

        self.assertIn(
            self.client.post(
                reverse("locations"),
                {
                    "name": "Site Created",
                    "department": str(self.other_dept.public_id),
                }
            ).status_code,
            [200, 201, 204],
        )

        self.assertIn(
            self.client.patch(
                self.other_url,
                {"department": str(self.dept.public_id)}
            ).status_code,
            [200, 204],
        )
