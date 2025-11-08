from django.test import TestCase
from django.contrib.auth import get_user_model
from db_inventory.permissions.helpers import (
    has_hierarchy_permission,
    is_in_scope,
    check_permission, ensure_permission
)
from db_inventory.factories import UserFactory, RoomFactory, LocationFactory, DepartmentFactory, AdminUserFactory
from db_inventory.models import User, Room, Location, Department, RoleAssignment

class GlobalPermissionTests(TestCase):

    def setUp(self):
        # Core structure: one department, two locations, two rooms
        self.dept1 = DepartmentFactory(name = "Chemistry")
        self.dept2 = DepartmentFactory(name = "Biology")

        self.loc1 = LocationFactory(name="Building A", department=self.dept1)
        self.loc2 = LocationFactory(name="Building B", department=self.dept2)

        self.room1 = RoomFactory(name="Lab 101", location=self.loc1)
        self.room2 = RoomFactory(name="Lab 202", location=self.loc2)

        # Create normal user
        self.user = UserFactory()
        # Create Admin account
        self.admin_user = AdminUserFactory()
        # Create a role for admin_user
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.admin_user, role="SITE_ADMIN"
        )
        # make that thier active role and save
        self.admin_user.active_role = self.site_admin_role
        self.site_admin_role.save()


    def test_hierarchy_respects_order(self):
            
            self.assertTrue(has_hierarchy_permission("ROOM_ADMIN", "ROOM_VIEWER"))
            self.assertTrue(has_hierarchy_permission("ROOM_ADMIN", "ROOM_CLERK"))
            self.assertFalse(has_hierarchy_permission("ROOM_VIEWER", "ROOM_ADMIN"))
            self.assertTrue(has_hierarchy_permission("LOCATION_ADMIN", "ROOM_ADMIN"))
            self.assertTrue(has_hierarchy_permission("DEPARTMENT_ADMIN", "LOCATION_ADMIN"))
            self.assertFalse(has_hierarchy_permission("LOCATION_ADMIN", "DEPARTMENT_VIEWER"))



    def test_site_admin_always_allowed(self):
        """SITE_ADMIN should always pass hierarchy check"""
        self.assertTrue(has_hierarchy_permission("SITE_ADMIN", "ROOM_ADMIN"))
        self.assertTrue(has_hierarchy_permission("SITE_ADMIN", "DEPARTMENT_ADMIN"))


    def test_scope_room_to_area_in_scope(self):
        """Room-level role should access assets in its scope"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_ADMIN", room=self.room1)
        self.assertTrue(is_in_scope(role, location=self.loc1))

    def test_scope_room_to_area_out_of_scope(self):
        """Room-level role should NOT access assets in another area"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_ADMIN", room=self.room2)
        self.assertFalse(is_in_scope(role, location=self.loc1))

    def test_scope_department_to_room(self):
        """Department-level role can access areas under its department"""
        role = RoleAssignment.objects.create(user=self.user, role="DEPARTMENT_ADMIN", department=self.dept1)
        self.assertTrue(is_in_scope(role, room=self.room1))
        self.assertTrue(is_in_scope(role, location=self.loc1))

    def test_scope_department_out_of_scope(self):
        """Department-level roles should not be able to access areas outside thier scope"""
        role = RoleAssignment.objects.create(user=self.user, role="DEPARTMENT_VIEWER", department=self.dept1)
        self.assertFalse(is_in_scope(role, room=self.room2))
        self.assertFalse(is_in_scope(role, location=self.loc2))

    
    def test_check_permission_with_hierarchy_and_scope(self):
        """Role passes only if both hierarchy and scope match"""
        role = RoleAssignment.objects.create(user=self.user, role="ROOM_ADMIN", room=self.room1)
        self.user.active_role = role
        self.user.save()

        # inside scope
        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        # outside scope
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room2))

    def test_site_admin_bypass_scope(self):
        """SITE_ADMIN does not care about scope, can access it ALL"""
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room1))
        self.assertTrue(check_permission(self.admin_user, "DEPARTMENT_ADMIN", room=self.dept2))
        self.assertTrue(check_permission(self.admin_user, "LOCATION_ADMIN", room=self.loc1))
       
    def test_missing_active_role_fails_permission(self):
        """If user has no active role, deny access"""
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))
       

    def test_hierarchy_cannot_override_scope(self):
        """Higher role in one department cannot act in another"""
        role = RoleAssignment.objects.create(user=self.user, role="DEPARTMENT_ADMIN", department=self.dept2)
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.room1))

