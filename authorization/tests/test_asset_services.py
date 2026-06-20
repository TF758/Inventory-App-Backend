# authorization/tests/test_asset_services.py

from django.test import TestCase

from authorization.models import (
    Permission,
    Role,
    RolePermission,
)

from authorization.services.assets import (
    has_asset_custody_scope,
    can_assign_asset_to_user,
    can_soft_delete_asset,
    can_hard_delete_asset,
)

from assets.asset_factories import EquipmentFactory
from users.factories.user_factories import (
    UserFactory,
    AdminUserFactory,
)

from users.models.roles import RoleAssignment

from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)

from sites.models.sites import UserPlacement


class AssetServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        # =====================================================
        # Scope hierarchy
        # =====================================================

        cls.department_a = DepartmentFactory()
        cls.location_a = LocationFactory(
            department=cls.department_a,
        )

        cls.room_a = RoomFactory(
            location=cls.location_a,
        )

        cls.room_a2 = RoomFactory(
            location=cls.location_a,
        )

        cls.department_b = DepartmentFactory()
        cls.location_b = LocationFactory(
            department=cls.department_b,
        )

        cls.room_b = RoomFactory(
            location=cls.location_b,
        )

        # =====================================================
        # Assets
        # =====================================================

        cls.asset_a = EquipmentFactory(
            room=cls.room_a,
        )

        cls.asset_b = EquipmentFactory(
            room=cls.room_b,
        )

        # =====================================================
        # Permission setup
        # =====================================================

        cls.assets_delete_permission = Permission.objects.create(
            code="assets.delete",
            name="Delete Assets",
            module="assets",
        )

        cls.assets_hard_delete_permission = Permission.objects.create(
            code="assets.hard_delete",
            name="Hard Delete Assets",
            module="assets",
        )

        cls.delete_role = Role.objects.create(
            code="DELETE_ROLE",
            name="Delete Role",
            scope_type="DEPARTMENT",
            level=10,
        )

        RolePermission.objects.create(
            role=cls.delete_role,
            permission=cls.assets_delete_permission,
        )

        cls.hard_delete_role = Role.objects.create(
            code="HARD_DELETE_ROLE",
            name="Hard Delete Role",
            scope_type="DEPARTMENT",
            level=20,
        )

        RolePermission.objects.create(
            role=cls.hard_delete_role,
            permission=cls.assets_hard_delete_permission,
        )

        # =====================================================
        # Admin users
        # =====================================================

        cls.department_admin_user = UserFactory()

        cls.department_admin_role = RoleAssignment.objects.create(
            user=cls.department_admin_user,
            role="DEPARTMENT_ADMIN",
            role_ref=cls.delete_role,
            department=cls.department_a,
        )

        cls.department_admin_user.active_role = (
            cls.department_admin_role
        )
        cls.department_admin_user.save()

        cls.location_admin_user = UserFactory()

        cls.location_admin_role = RoleAssignment.objects.create(
            user=cls.location_admin_user,
            role="LOCATION_ADMIN",
            location=cls.location_a,
        )

        cls.location_admin_user.active_role = (
            cls.location_admin_role
        )
        cls.location_admin_user.save()

        cls.room_admin_user = UserFactory()

        cls.room_admin_role = RoleAssignment.objects.create(
            user=cls.room_admin_user,
            role="ROOM_ADMIN",
            room=cls.room_a,
        )

        cls.room_admin_user.active_role = (
            cls.room_admin_role
        )
        cls.room_admin_user.save()

        cls.site_admin_user = AdminUserFactory()

        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin_user,
            role="SITE_ADMIN",
        )

        cls.site_admin_user.active_role = (
            cls.site_admin_role
        )
        cls.site_admin_user.save()

        # =====================================================
        # Users for assignment testing
        # =====================================================

        cls.user_in_room = UserFactory()

        UserPlacement.objects.create(
            user=cls.user_in_room,
            room=cls.room_a,
            is_current=True,
        )

        cls.user_in_other_room = UserFactory()

        UserPlacement.objects.create(
            user=cls.user_in_other_room,
            room=cls.room_b,
            is_current=True,
        )

        # =====================================================
        # Hard delete user
        # =====================================================

        cls.hard_delete_user = UserFactory()

        cls.hard_delete_assignment = RoleAssignment.objects.create(
            user=cls.hard_delete_user,
            role="DEPARTMENT_ADMIN",
            role_ref=cls.hard_delete_role,
            department=cls.department_a,
        )

        cls.hard_delete_user.active_role = (
            cls.hard_delete_assignment
        )
        cls.hard_delete_user.save()

    # =====================================================
    # has_asset_custody_scope
    # =====================================================

    def test_department_role_has_custody_within_department(self):

        self.assertTrue(
            has_asset_custody_scope(
                self.department_admin_role,
                self.asset_a,
            )
        )

    def test_department_role_denied_outside_department(self):

        self.assertFalse(
            has_asset_custody_scope(
                self.department_admin_role,
                self.asset_b,
            )
        )

    def test_location_role_has_custody_within_location(self):

        self.assertTrue(
            has_asset_custody_scope(
                self.location_admin_role,
                self.asset_a,
            )
        )

    def test_location_role_denied_outside_location(self):

        self.assertFalse(
            has_asset_custody_scope(
                self.location_admin_role,
                self.asset_b,
            )
        )

    def test_room_role_has_custody_for_own_room(self):

        self.assertTrue(
            has_asset_custody_scope(
                self.room_admin_role,
                self.asset_a,
            )
        )

    def test_room_role_denied_for_other_room(self):

        self.assertFalse(
            has_asset_custody_scope(
                self.room_admin_role,
                self.asset_b,
            )
        )

    def test_site_admin_has_full_custody_scope(self):

        self.assertTrue(
            has_asset_custody_scope(
                self.site_admin_role,
                self.asset_b,
            )
        )

    # =====================================================
    # can_assign_asset_to_user
    # =====================================================

    def test_room_admin_can_assign_to_user_in_same_room(self):

        self.assertTrue(
            can_assign_asset_to_user(
                self.room_admin_role,
                self.user_in_room,
            )
        )

    def test_room_admin_cannot_assign_to_user_outside_room(self):

        self.assertFalse(
            can_assign_asset_to_user(
                self.room_admin_role,
                self.user_in_other_room,
            )
        )

    def test_department_admin_can_assign_within_department(self):

        self.assertTrue(
            can_assign_asset_to_user(
                self.department_admin_role,
                self.user_in_room,
            )
        )

    def test_department_admin_cannot_assign_outside_department(self):

        self.assertFalse(
            can_assign_asset_to_user(
                self.department_admin_role,
                self.user_in_other_room,
            )
        )

    def test_site_admin_can_assign_anywhere(self):

        self.assertTrue(
            can_assign_asset_to_user(
                self.site_admin_role,
                self.user_in_other_room,
            )
        )

    # =====================================================
    # can_soft_delete_asset
    # =====================================================

    def test_soft_delete_allowed_with_permission_and_scope(self):

        self.assertTrue(
            can_soft_delete_asset(
                self.department_admin_user,
                self.asset_a,
            )
        )

    def test_soft_delete_denied_outside_scope(self):

        self.assertFalse(
            can_soft_delete_asset(
                self.department_admin_user,
                self.asset_b,
            )
        )

    # =====================================================
    # can_hard_delete_asset
    # =====================================================

    def test_hard_delete_allowed_with_permission(self):

        self.assertTrue(
            can_hard_delete_asset(
                self.hard_delete_user,
                self.asset_a,
            )
        )

    def test_hard_delete_denied_without_permission(self):

        self.assertFalse(
            can_hard_delete_asset(
                self.department_admin_user,
                self.asset_a,
            )
        )