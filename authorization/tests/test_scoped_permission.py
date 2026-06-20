from types import SimpleNamespace
from django.test import TestCase
from authorization.models import Permission, Role, RolePermission
from authorization.permissions.base_permissions import ScopedPermission
from users.factories.user_factories import  UserFactory, AdminUserFactory
from users.models.roles import RoleAssignment
from sites.factories.site_factories import  DepartmentFactory, LocationFactory, RoomFactory 

class CustomScopedPermission(ScopedPermission):

    permission_map = {
        "GET": "assets.view",
    }

    def get_scope_object(self, obj):
        return obj.custom_room

class DummyPermission(ScopedPermission):
    permission_map = {
        "GET": "assets.view",
        "POST": "assets.create",
    }


class ScopedPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.department = DepartmentFactory()

        cls.assets_view = Permission.objects.create(
            code="assets.view",
            name="View Assets",
            module="assets",
        )

        cls.assets_create = Permission.objects.create(
            code="assets.create",
            name="Create Assets",
            module="assets",
        )

        cls.role = Role.objects.create(
            code="TEST_ROLE",
            name="Test Role",
            scope_type="DEPARTMENT",
            level=10,
        )

        RolePermission.objects.create(
            role=cls.role,
            permission=cls.assets_view,
        )

        cls.user = UserFactory()

        assignment = RoleAssignment.objects.create(
            user=cls.user,
            role="DEPARTMENT_VIEWER",
            role_ref=cls.role,
            department=cls.department,
        )

        cls.user.active_role = assignment
        cls.user.save()

        cls.site_admin = AdminUserFactory()

        site_admin_assignment = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )

        cls.site_admin.active_role = site_admin_assignment
        cls.site_admin.save()

        cls.permission = DummyPermission()

    def make_request(self, method, user):
        return SimpleNamespace(
            method=method,
            user=user,
        )

    # =====================================================
    # Permission mapping
    # =====================================================

    def test_get_permission_code_for_get(self):
        request = self.make_request(
            "GET",
            self.user,
        )

        self.assertEqual(
            self.permission.get_permission_code(request),
            "assets.view",
        )

    def test_get_permission_code_for_post(self):
        request = self.make_request(
            "POST",
            self.user,
        )

        self.assertEqual(
            self.permission.get_permission_code(request),
            "assets.create",
        )

    # =====================================================
    # has_permission
    # =====================================================

    def test_get_allowed_when_permission_exists(self):
        request = self.make_request(
            "GET",
            self.user,
        )

        self.assertTrue(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    def test_post_denied_when_permission_missing(self):
        request = self.make_request(
            "POST",
            self.user,
        )

        self.assertFalse(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    def test_unknown_method_denied(self):
        request = self.make_request(
            "DELETE",
            self.user,
        )

        self.assertFalse(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    def test_anonymous_user_denied(self):

        anonymous = SimpleNamespace(
            is_authenticated=False,
        )

        request = self.make_request(
            "GET",
            anonymous,
        )

        self.assertFalse(
            self.permission.has_permission(
                request,
                view=None,
            )
        )

    # =====================================================
    # has_object_permission
    # =====================================================

    def test_object_without_scope_is_denied(self):

        request = self.make_request(
            "GET",
            self.user,
        )

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                view=None,
                obj=object(),
            )
        )

    def test_site_admin_bypass_object_permission(self):

        request = self.make_request(
            "GET",
            self.site_admin,
        )

        self.assertTrue(
            self.permission.has_object_permission(
                request,
                view=None,
                obj=object(),
            )
        )


    def test_object_in_scope_is_allowed(self):

        location = LocationFactory(
            department=self.department,
        )

        room = RoomFactory(
            location=location,
        )

        obj = SimpleNamespace(
            room=room,
        )

        request = self.make_request(
            "GET",
            self.user,
        )

        self.assertTrue(
            self.permission.has_object_permission(
                request,
                view=None,
                obj=obj,
            )
        )

    def test_object_out_of_scope_is_denied(self):

        other_department = DepartmentFactory()

        location = LocationFactory(
            department=other_department,
        )

        room = RoomFactory(
            location=location,
        )

        obj = SimpleNamespace(
            room=room,
        )

        request = self.make_request(
            "GET",
            self.user,
        )

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                view=None,
                obj=obj,
            )
        )


    def test_custom_scope_object_is_used(self):

            permission = CustomScopedPermission()

            location = LocationFactory( department=self.department )

            room = RoomFactory( location=location )

            obj = SimpleNamespace( custom_room=room )

            request = self.make_request( "GET", self.user, )

            self.assertTrue(
                permission.has_object_permission(
                    request,
                    view=None,
                    obj=obj,
                )
            )