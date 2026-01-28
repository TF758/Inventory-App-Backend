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

    def test_location_admin_access_own_location(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "LOCATION_VIEWER", location=self.loc1))
        self.assertTrue(is_in_scope(role, location=self.loc1))

    def test_location_admin_access_own_rooms(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(role, room=self.room1))

    def test_location_admin_cannot_access_other_location(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "LOCATION_VIEWER", location=self.loc2))
        self.assertFalse(is_in_scope(role, location=self.loc2))

    def test_location_admin_cannot_access_rooms_outside_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.room2))
        self.assertFalse(is_in_scope(role, room=self.room2))

    def test_site_admin_bypass_location_scope(self):
        self.assertTrue(check_permission(self.admin_user, "LOCATION_ADMIN", location=self.loc1))
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room2))
        self.assertTrue(is_in_scope(self.site_admin_role, location=self.loc2))
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room1))

    def test_missing_active_role_denied(self):
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))

    def test_ensure_permission_raises_for_out_of_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc1,
        )
        self.user.active_role = role
        self.user.save()

        with self.assertRaises(PermissionDenied):
            ensure_permission(self.user, "ROOM_ADMIN", room=self.room2)


class LocationViewerTests(TestCase):
    """
    Tests for LocationViewer role.
    """

    @classmethod
    def setUpTestData(cls):
        cls.dept1 = DepartmentFactory(name="Chemistry")
        cls.loc1 = LocationFactory(name="Building A", department=cls.dept1)
        cls.room1 = RoomFactory(name="Lab 101", location=cls.loc1)

        cls.user = UserFactory()
        cls.role = RoleAssignment.objects.create(
            user=cls.user,
            role="LOCATION_VIEWER",
            location=cls.loc1,
        )
        cls.user.active_role = cls.role
        cls.user.save()

    def test_location_viewer_can_view_location(self):
        self.assertTrue(check_permission(self.user, "LOCATION_VIEWER", location=self.loc1))
        self.assertTrue(is_in_scope(self.role, location=self.loc1))

    def test_location_viewer_cannot_create_location(self):
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))

    def test_location_viewer_cannot_update_location(self):
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))

    def test_location_viewer_cannot_delete_location(self):
        self.assertFalse(check_permission(self.user, "LOCATION_ADMIN", location=self.loc1))

    def test_location_viewer_can_view_rooms_in_scope(self):
        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertTrue(is_in_scope(self.role, room=self.room1))

    def test_location_viewer_cannot_create_update_delete_room(self):
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

    @classmethod
    def setUpTestData(cls):
        cls.dept = DepartmentFactory(name="Physics")
        cls.other_dept = DepartmentFactory(name="Other Dept")

        cls.loc = LocationFactory(name="Building A", department=cls.dept)
        cls.other_loc = LocationFactory(name="Building B", department=cls.other_dept)

        cls.viewer = UserFactory()
        cls.loc_admin = UserFactory()
        cls.dep_admin = UserFactory()
        cls.site_admin = AdminUserFactory()

        cls.viewer.active_role = RoleAssignment.objects.create(
            user=cls.viewer,
            role="LOCATION_VIEWER",
            location=cls.loc,
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

        for u in (cls.viewer, cls.loc_admin, cls.dep_admin, cls.site_admin):
            u.save()

        cls.url = reverse("location-detail", args=[cls.loc.public_id])
        cls.other_url = reverse("location-detail", args=[cls.other_loc.public_id])

    def setUp(self):
            self.client = APIClient()
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
