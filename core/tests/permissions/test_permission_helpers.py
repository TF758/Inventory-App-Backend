from django.test import TestCase
from core.permissions.helpers import (
    has_hierarchy_permission,
    is_in_scope,
    check_permission,
    ensure_permission,
    is_admin_role,
    is_viewer_role,
)
from rest_framework.exceptions import PermissionDenied
from users.factories.user_factories import UserFactory, AdminUserFactory
from users.models.roles import RoleAssignment
from sites.factories.site_factories import DepartmentFactory, LocationFactory, RoomFactory


class PermissionHelperTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Hierarchy
        cls.dept = DepartmentFactory()
        cls.other_dept = DepartmentFactory()

        cls.loc = LocationFactory(department=cls.dept)
        cls.other_loc = LocationFactory(department=cls.other_dept)

        cls.room = RoomFactory(location=cls.loc)
        cls.other_room = RoomFactory(location=cls.other_loc)

        # Users
        cls.user = UserFactory()
        cls.site_admin = AdminUserFactory()

        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )
        cls.site_admin.active_role = cls.site_admin_role
        cls.site_admin.save()

    # -------------------------
    # Hierarchy
    # -------------------------

    def test_hierarchy_positive(self):
        self.assertTrue(has_hierarchy_permission("ROOM_ADMIN", "ROOM_VIEWER"))
        self.assertTrue(has_hierarchy_permission("LOCATION_ADMIN", "ROOM_ADMIN"))

    def test_hierarchy_negative(self):
        self.assertFalse(has_hierarchy_permission("ROOM_VIEWER", "ROOM_ADMIN"))
        self.assertFalse(has_hierarchy_permission("LOCATION_ADMIN", "DEPARTMENT_ADMIN"))

    def test_site_admin_hierarchy_override(self):
        self.assertTrue(has_hierarchy_permission("SITE_ADMIN", "ROOM_ADMIN"))

    # -------------------------
    # Role helpers
    # -------------------------

    def test_is_admin_role(self):
        self.assertTrue(is_admin_role("ROOM_ADMIN"))
        self.assertFalse(is_admin_role("ROOM_VIEWER"))

    def test_is_viewer_role(self):
        self.assertTrue(is_viewer_role("ROOM_VIEWER"))
        self.assertFalse(is_viewer_role("ROOM_ADMIN"))

    # -------------------------
    # Scope logic
    # -------------------------

    def test_room_scope_exact(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.assertTrue(is_in_scope(role, room=self.room))
        self.assertFalse(is_in_scope(role, room=self.other_room))

    def test_location_scope_includes_rooms(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc,
        )
        self.assertTrue(is_in_scope(role, room=self.room))
        self.assertFalse(is_in_scope(role, room=self.other_room))

    def test_department_scope_includes_all(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept,
        )
        self.assertTrue(is_in_scope(role, location=self.loc))
        self.assertTrue(is_in_scope(role, room=self.room))
        self.assertFalse(is_in_scope(role, room=self.other_room))

    def test_site_admin_scope_always_true(self):
        self.assertTrue(is_in_scope(self.site_admin_role, room=self.room))
        self.assertTrue(is_in_scope(self.site_admin_role, location=self.other_loc))

    # -------------------------
    # Permission checks
    # -------------------------

    def test_check_permission_success(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        self.assertTrue(check_permission(self.user, "ROOM_VIEWER", room=self.room))

    def test_check_permission_fails_scope(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        self.assertFalse(check_permission(self.user, "ROOM_VIEWER", room=self.other_room))

    def test_check_permission_missing_role(self):
        self.assertFalse(check_permission(self.user, "ROOM_ADMIN", room=self.room))

    def test_site_admin_permission_bypass(self):
        self.assertTrue(check_permission(self.site_admin, "ROOM_ADMIN", room=self.room))
        self.assertTrue(check_permission(self.site_admin, "DEPARTMENT_ADMIN", department=self.other_dept))

    # -------------------------
    # ensure_permission
    # -------------------------

    def test_ensure_permission_passes(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        ensure_permission(self.user, "ROOM_VIEWER", room=self.room)  # should not raise

    def test_ensure_permission_raises(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        with self.assertRaises(PermissionDenied):
            ensure_permission(self.user, "ROOM_VIEWER", room=self.other_room)