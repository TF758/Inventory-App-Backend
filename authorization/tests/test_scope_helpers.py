# authorization/tests/test_scope_helpers.py

from django.test import TestCase

from authorization.helpers import (
    is_in_scope,
    is_user_in_scope,
)

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


class ScopeHelperTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        # -----------------------------
        # Department A
        # -----------------------------

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

        # -----------------------------
        # Department B
        # -----------------------------

        cls.department_b = DepartmentFactory()

        cls.location_b = LocationFactory(
            department=cls.department_b,
        )

        cls.room_b = RoomFactory(
            location=cls.location_b,
        )

        # -----------------------------
        # Users
        # -----------------------------

        cls.department_admin_user = UserFactory()

        cls.location_admin_user = UserFactory()

        cls.room_admin_user = UserFactory()

        cls.site_admin_user = AdminUserFactory()

        # -----------------------------
        # Role Assignments
        # -----------------------------

        cls.department_role = RoleAssignment.objects.create(
            user=cls.department_admin_user,
            role="DEPARTMENT_ADMIN",
            department=cls.department_a,
        )

        cls.location_role = RoleAssignment.objects.create(
            user=cls.location_admin_user,
            role="LOCATION_ADMIN",
            location=cls.location_a,
        )

        cls.room_role = RoleAssignment.objects.create(
            user=cls.room_admin_user,
            role="ROOM_ADMIN",
            room=cls.room_a,
        )

        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin_user,
            role="SITE_ADMIN",
        )

    # =====================================================
    # is_in_scope
    # =====================================================

    def test_none_role_returns_false(self):

        self.assertFalse(
            is_in_scope(
                None,
                room=self.room_a,
            )
        )

    def test_site_admin_has_scope_everywhere(self):

        self.assertTrue(
            is_in_scope(
                self.site_admin_role,
                room=self.room_b,
            )
        )

        self.assertTrue(
            is_in_scope(
                self.site_admin_role,
                location=self.location_b,
            )
        )

        self.assertTrue(
            is_in_scope(
                self.site_admin_role,
                department=self.department_b,
            )
        )

    # -----------------------------
    # Department scope
    # -----------------------------

    def test_department_role_covers_department(self):

        self.assertTrue(
            is_in_scope(
                self.department_role,
                department=self.department_a,
            )
        )

    def test_department_role_covers_location_in_department(self):

        self.assertTrue(
            is_in_scope(
                self.department_role,
                location=self.location_a,
            )
        )

    def test_department_role_covers_room_in_department(self):

        self.assertTrue(
            is_in_scope(
                self.department_role,
                room=self.room_a,
            )
        )

    def test_department_role_does_not_cover_other_department(self):

        self.assertFalse(
            is_in_scope(
                self.department_role,
                department=self.department_b,
            )
        )

    # -----------------------------
    # Location scope
    # -----------------------------

    def test_location_role_covers_location(self):

        self.assertTrue(
            is_in_scope(
                self.location_role,
                location=self.location_a,
            )
        )

    def test_location_role_covers_room_in_location(self):

        self.assertTrue(
            is_in_scope(
                self.location_role,
                room=self.room_a,
            )
        )

    def test_location_role_does_not_cover_other_location(self):

        self.assertFalse(
            is_in_scope(
                self.location_role,
                location=self.location_b,
            )
        )

    # -----------------------------
    # Room scope
    # -----------------------------

    def test_room_role_covers_own_room(self):

        self.assertTrue(
            is_in_scope(
                self.room_role,
                room=self.room_a,
            )
        )

    def test_room_role_does_not_cover_sibling_room(self):

        self.assertFalse(
            is_in_scope(
                self.room_role,
                room=self.room_a2,
            )
        )

    def test_room_role_does_not_cover_other_location_room(self):

        self.assertFalse(
            is_in_scope(
                self.room_role,
                room=self.room_b,
            )
        )

    # =====================================================
    # is_user_in_scope
    # =====================================================

    def test_user_in_scope_via_role_assignment(self):

        target_user = UserFactory()

        RoleAssignment.objects.create(
            user=target_user,
            role="ROOM_VIEWER",
            room=self.room_a,
        )

        self.assertTrue(
            is_user_in_scope(
                self.department_role,
                target_user,
            )
        )

    def test_user_in_scope_via_user_placement(self):

        target_user = UserFactory()

        UserPlacement.objects.create(
            user=target_user,
            room=self.room_a,
            is_current=True,
        )

        self.assertTrue(
            is_user_in_scope(
                self.department_role,
                target_user,
            )
        )

    def test_user_out_of_scope_returns_false(self):

        target_user = UserFactory()

        UserPlacement.objects.create(
            user=target_user,
            room=self.room_b,
            is_current=True,
        )

        self.assertFalse(
            is_user_in_scope(
                self.department_role,
                target_user,
            )
        )

    def test_site_admin_user_scope_always_true(self):

        target_user = UserFactory()

        UserPlacement.objects.create(
            user=target_user,
            room=self.room_b,
            is_current=True,
        )

        self.assertTrue(
            is_user_in_scope(
                self.site_admin_role,
                target_user,
            )
        )

    def test_none_admin_role_returns_false(self):

        target_user = UserFactory()

        self.assertFalse(
            is_user_in_scope(
                None,
                target_user,
            )
        )