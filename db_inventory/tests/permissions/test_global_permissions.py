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

    @classmethod
    def setUpTestData(cls):
        # Core structure: one department, two locations, two rooms
        cls.dept1 = DepartmentFactory(name="Chemistry")
        cls.dept2 = DepartmentFactory(name="Biology")

        cls.loc1 = LocationFactory(name="Building A", department=cls.dept1)
        cls.loc2 = LocationFactory(name="Building B", department=cls.dept2)

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

    # ---------------- Tests ----------------

    def test_hierarchy_respects_order(self):
        self.assertTrue(has_hierarchy_permission("ROOM_ADMIN", "ROOM_VIEWER"))
        self.assertTrue(has_hierarchy_permission("ROOM_ADMIN", "ROOM_CLERK"))
        self.assertFalse(has_hierarchy_permission("ROOM_VIEWER", "ROOM_ADMIN"))
        self.assertTrue(has_hierarchy_permission("LOCATION_ADMIN", "ROOM_ADMIN"))
        self.assertTrue(has_hierarchy_permission("DEPARTMENT_ADMIN", "LOCATION_ADMIN"))
        self.assertFalse(has_hierarchy_permission("LOCATION_ADMIN", "DEPARTMENT_VIEWER"))

    def test_site_admin_always_allowed(self):
        self.assertTrue(has_hierarchy_permission("SITE_ADMIN", "ROOM_ADMIN"))
        self.assertTrue(has_hierarchy_permission("SITE_ADMIN", "DEPARTMENT_ADMIN"))

    def test_scope_room_to_area_in_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room1,
        )
        self.assertTrue(is_in_scope(role, location=self.loc1))

    def test_scope_room_to_area_out_of_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room2,
        )
        self.assertFalse(is_in_scope(role, location=self.loc1))

    def test_scope_department_to_room(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept1,
        )
        self.assertTrue(is_in_scope(role, room=self.room1))
        self.assertTrue(is_in_scope(role, location=self.loc1))

    def test_scope_department_out_of_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_VIEWER",
            department=self.dept1,
        )
        self.assertFalse(is_in_scope(role, room=self.room2))
        self.assertFalse(is_in_scope(role, location=self.loc2))

    def test_check_permission_with_hierarchy_and_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room1,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room2))

    def test_site_admin_bypass_scope(self):
        self.assertTrue(check_permission(self.admin_user, "ROOM_ADMIN", room=self.room1))
        self.assertTrue(check_permission(self.admin_user, "DEPARTMENT_ADMIN", room=self.dept2))
        self.assertTrue(check_permission(self.admin_user, "LOCATION_ADMIN", room=self.loc1))

    def test_missing_active_role_fails_permission(self):
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room1))

    def test_hierarchy_cannot_override_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept2,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.room1))
