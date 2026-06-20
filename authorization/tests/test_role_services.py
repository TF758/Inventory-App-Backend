# authorization/tests/test_role_delegation.py

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from authorization.models import Permission, Role, RolePermission
from authorization.services.role import can_assign_role, can_delete_role_assignment, can_grant_role, can_manage_role_assignment, can_update_role_assignment, ensure_can_assign_role
from users.factories.user_factories import  UserFactory, AdminUserFactory

from users.models.roles import RoleAssignment

from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)


class RoleDelegationTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        # =====================================================
        # Scope hierarchy
        # =====================================================

        cls.department = DepartmentFactory()

        cls.location = LocationFactory(
            department=cls.department,
        )

        cls.room = RoomFactory(
            location=cls.location,
        )

        cls.other_department = DepartmentFactory()

        cls.other_location = LocationFactory(
            department=cls.other_department,
        )

        cls.other_room = RoomFactory(
            location=cls.other_location,
        )

        # =====================================================
        # Permissions
        # =====================================================

        cls.view_permission = Permission.objects.create(
            code="users.view",
            name="View Users",
            module="users",
        )

        cls.delete_permission = Permission.objects.create(
            code="users.delete",
            name="Delete Users",
            module="users",
        )

        # =====================================================
        # Roles
        # =====================================================

        cls.admin_role_ref = Role.objects.create(
            code="DEPT_ADMIN",
            name="Department Admin",
            scope_type="DEPARTMENT",
            level=60,
        )

        cls.viewer_role_ref = Role.objects.create(
            code="ROOM_VIEWER",
            name="Room Viewer",
            scope_type="ROOM",
            level=10,
        )

        cls.peer_role_ref = Role.objects.create(
            code="PEER_ADMIN",
            name="Peer Admin",
            scope_type="DEPARTMENT",
            level=60,
        )

        cls.super_role_ref = Role.objects.create(
            code="SUPER_ADMIN",
            name="Super Admin",
            scope_type="DEPARTMENT",
            level=80,
        )

        # admin role permissions

        RolePermission.objects.create(
            role=cls.admin_role_ref,
            permission=cls.view_permission,
        )

        RolePermission.objects.create(
            role=cls.admin_role_ref,
            permission=cls.delete_permission,
        )

        # viewer role permissions

        RolePermission.objects.create(
            role=cls.viewer_role_ref,
            permission=cls.view_permission,
        )

        # super role permissions

        RolePermission.objects.create(
            role=cls.super_role_ref,
            permission=cls.view_permission,
        )

        RolePermission.objects.create(
            role=cls.super_role_ref,
            permission=cls.delete_permission,
        )

        # =====================================================
        # Actor
        # =====================================================

        cls.actor = UserFactory()

        cls.actor_assignment = RoleAssignment.objects.create(
            user=cls.actor,
            role="DEPARTMENT_ADMIN",
            role_ref=cls.admin_role_ref,
            department=cls.department,
        )

        cls.actor.active_role = cls.actor_assignment
        cls.actor.save()

        # =====================================================
        # Site admin
        # =====================================================

        cls.site_admin = AdminUserFactory()

        cls.site_admin_assignment = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )

        cls.site_admin.active_role = (
            cls.site_admin_assignment
        )
        cls.site_admin.save()

        # =====================================================
        # Assignments to manage
        # =====================================================

        cls.lower_assignment = RoleAssignment.objects.create(
            user=UserFactory(),
            role="ROOM_VIEWER",
            role_ref=cls.viewer_role_ref,
            room=cls.room,
        )

        cls.peer_assignment = RoleAssignment.objects.create(
            user=UserFactory(),
            role="DEPARTMENT_ADMIN",
            role_ref=cls.peer_role_ref,
            department=cls.department,
        )

        cls.higher_assignment = RoleAssignment.objects.create(
            user=UserFactory(),
            role="SITE_ADMIN",
            role_ref=cls.super_role_ref,
        )

    # =====================================================
    # can_manage_role_assignment
    # =====================================================

    def test_can_manage_lower_level_assignment(self):

        self.assertTrue(
            can_manage_role_assignment(
                self.actor,
                self.lower_assignment,
            )
        )

    def test_cannot_manage_peer_assignment(self):

        self.assertFalse(
            can_manage_role_assignment(
                self.actor,
                self.peer_assignment,
            )
        )

    def test_cannot_manage_higher_assignment(self):

        self.assertFalse(
            can_manage_role_assignment(
                self.actor,
                self.higher_assignment,
            )
        )

    def test_site_admin_can_manage_any_assignment(self):

        self.assertTrue(
            can_manage_role_assignment(
                self.site_admin,
                self.higher_assignment,
            )
        )

    # =====================================================
    # can_grant_role
    # =====================================================

    def test_can_grant_subset_role(self):

        self.assertTrue(
            can_grant_role(
                self.actor,
                self.viewer_role_ref,
            )
        )

    def test_cannot_grant_role_with_permissions_not_possessed(self):

        restricted_role = Role.objects.create(
            code="RESTRICTED",
            name="Restricted",
            scope_type="DEPARTMENT",
            level=30,
        )

        extra_permission = Permission.objects.create(
            code="secret.permission",
            name="Secret",
            module="test",
        )

        RolePermission.objects.create(
            role=restricted_role,
            permission=extra_permission,
        )

        self.assertFalse(
            can_grant_role(
                self.actor,
                restricted_role,
            )
        )

    def test_site_admin_can_grant_any_role(self):

        self.assertTrue(
            can_grant_role(
                self.site_admin,
                self.super_role_ref,
            )
        )

    # =====================================================
    # can_assign_role
    # =====================================================

    def test_can_assign_role_in_scope(self):

        self.assertTrue(
            can_assign_role(
                actor=self.actor,
                target_role=self.viewer_role_ref,
                room=self.room,
            )
        )

    def test_cannot_assign_role_outside_scope(self):

        self.assertFalse(
            can_assign_role(
                actor=self.actor,
                target_role=self.viewer_role_ref,
                room=self.other_room,
            )
        )

    # =====================================================
    # can_update_role_assignment
    # =====================================================

    def test_can_update_lower_assignment(self):

        self.assertTrue(
            can_update_role_assignment(
                actor=self.actor,
                assignment=self.lower_assignment,
            )
        )

    def test_cannot_update_peer_assignment(self):

        self.assertFalse(
            can_update_role_assignment(
                actor=self.actor,
                assignment=self.peer_assignment,
            )
        )

    def test_cannot_update_outside_scope(self):

        outside_assignment = RoleAssignment.objects.create(
            user=UserFactory(),
            role="ROOM_VIEWER",
            role_ref=self.viewer_role_ref,
            room=self.other_room,
        )

        self.assertFalse(
            can_update_role_assignment(
                actor=self.actor,
                assignment=outside_assignment,
            )
        )

    # =====================================================
    # can_delete_role_assignment
    # =====================================================

    def test_can_delete_lower_assignment(self):

        self.assertTrue(
            can_delete_role_assignment(
                actor=self.actor,
                assignment=self.lower_assignment,
            )
        )

    def test_cannot_delete_peer_assignment(self):

        self.assertFalse(
            can_delete_role_assignment(
                actor=self.actor,
                assignment=self.peer_assignment,
            )
        )

    # =====================================================
    # ensure wrappers
    # =====================================================

    def test_ensure_can_assign_role_raises(self):

        with self.assertRaises(PermissionDenied):
            ensure_can_assign_role(
                actor=self.actor,
                target_role=self.viewer_role_ref,
                room=self.other_room,
            )