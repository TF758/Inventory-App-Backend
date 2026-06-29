from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.permissions.sites import (
    DepartmentContextPermission,
    LocationContextPermission,
    RoomContextPermission,
)
from sites.models.sites import (
    Department,
    Location,
    Room,
)


class DepartmentContextPermissionTests(SimpleTestCase):
    """
    Lean tests for DepartmentContextPermission.

    Context permissions do not check capabilities. They only verify:

        - active_role exists
        - hierarchy level is allowed
        - optional public_id context is inside actor scope

    DepartmentContextPermission is the simplest variant because it only
    compares actor.department_id to department.id.
    """

    def make_role_assignment(
        self,
        role="DEPARTMENT_ADMIN",
        *,
        department_id=None,
        location_id=None,
        room_id=None,
    ):
        return SimpleNamespace(
            role=role,
            department_id=department_id,
            location_id=location_id,
            room_id=room_id,
        )

    def make_user(self, *, active_role=None):
        return SimpleNamespace(
            active_role=active_role,
        )

    def make_request(self, *, user=None):
        return SimpleNamespace(
            user=user,
        )

    def make_view(self, *, public_id=None):
        kwargs = {}

        if public_id is not None:
            kwargs["public_id"] = public_id

        return SimpleNamespace(
            kwargs=kwargs,
        )

    def make_department(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_department")
    def test_returns_false_without_active_role(
        self,
        mock_can_access_department,
    ):
        permission = DepartmentContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=None),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_department.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_department")
    def test_returns_false_when_hierarchy_denies_department_access(
        self,
        mock_can_access_department,
    ):
        mock_can_access_department.return_value = False

        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        permission = DepartmentContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_department.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_department")
    def test_returns_true_without_public_id_when_hierarchy_allows(
        self,
        mock_can_access_department,
        mock_get_object_or_404,
    ):
        mock_can_access_department.return_value = True

        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        permission = DepartmentContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view()

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_get_object_or_404.assert_not_called()

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_department")
    def test_site_admin_can_access_department_context(
        self,
        mock_can_access_department,
        mock_get_object_or_404,
    ):
        mock_can_access_department.return_value = True
        department = self.make_department(id=99)
        mock_get_object_or_404.return_value = department

        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        permission = DepartmentContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="DPT099",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_get_object_or_404.assert_called_once_with(
            Department,
            public_id="DPT099",
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_department")
    def test_department_actor_can_access_own_department_context(
        self,
        mock_can_access_department,
        mock_get_object_or_404,
    ):
        mock_can_access_department.return_value = True
        department = self.make_department(id=1)
        mock_get_object_or_404.return_value = department

        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        permission = DepartmentContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="DPT001",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_department")
    def test_department_actor_cannot_access_other_department_context(
        self,
        mock_can_access_department,
        mock_get_object_or_404,
    ):
        mock_can_access_department.return_value = True
        department = self.make_department(id=2)
        mock_get_object_or_404.return_value = department

        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        permission = DepartmentContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="DPT002",
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )


class LocationContextPermissionTests(SimpleTestCase):
    """
    Lean tests for LocationContextPermission.

    Location context adds two non-site scope paths:

        - department actor may access locations inside their department
        - location actor may access their own location
    """

    def make_role_assignment(
        self,
        role="LOCATION_ADMIN",
        *,
        department_id=None,
        location_id=None,
        room_id=None,
    ):
        return SimpleNamespace(
            role=role,
            department_id=department_id,
            location_id=location_id,
            room_id=room_id,
        )

    def make_user(self, *, active_role=None):
        return SimpleNamespace(
            active_role=active_role,
        )

    def make_request(self, *, user=None):
        return SimpleNamespace(
            user=user,
        )

    def make_view(self, *, public_id=None):
        kwargs = {}

        if public_id is not None:
            kwargs["public_id"] = public_id

        return SimpleNamespace(
            kwargs=kwargs,
        )

    def make_location(
        self,
        id=1,
        department_id=1,
    ):
        return SimpleNamespace(
            id=id,
            department_id=department_id,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_returns_false_without_active_role(
        self,
        mock_can_access_location,
    ):
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=None),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_location.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_returns_false_when_hierarchy_denies_location_access(
        self,
        mock_can_access_location,
    ):
        mock_can_access_location.return_value = False

        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_location.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_returns_true_without_public_id_when_hierarchy_allows(
        self,
        mock_can_access_location,
        mock_get_object_or_404,
    ):
        mock_can_access_location.return_value = True

        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view()

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_get_object_or_404.assert_not_called()

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_site_admin_can_access_location_context(
        self,
        mock_can_access_location,
        mock_get_object_or_404,
    ):
        mock_can_access_location.return_value = True
        location = self.make_location(
            id=99,
            department_id=99,
        )
        mock_get_object_or_404.return_value = location

        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="LOC099",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_get_object_or_404.assert_called_once_with(
            Location,
            public_id="LOC099",
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_department_actor_can_access_location_inside_department(
        self,
        mock_can_access_location,
        mock_get_object_or_404,
    ):
        mock_can_access_location.return_value = True
        location = self.make_location(
            id=10,
            department_id=1,
        )
        mock_get_object_or_404.return_value = location

        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="LOC010",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_location_actor_can_access_own_location(
        self,
        mock_can_access_location,
        mock_get_object_or_404,
    ):
        mock_can_access_location.return_value = True
        location = self.make_location(
            id=10,
            department_id=1,
        )
        mock_get_object_or_404.return_value = location

        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="LOC010",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_actor_cannot_access_location_outside_scope(
        self,
        mock_can_access_location,
        mock_get_object_or_404,
    ):
        mock_can_access_location.return_value = True
        location = self.make_location(
            id=20,
            department_id=2,
        )
        mock_get_object_or_404.return_value = location

        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        permission = LocationContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="LOC020",
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )


class RoomContextPermissionTests(SimpleTestCase):
    """
    Lean tests for RoomContextPermission.

    Room context delegates actual room scope to ScopeService.
    ScopeService already has the full role/scope matrix coverage.
    """

    def make_role_assignment(
        self,
        role="ROOM_ADMIN",
        *,
        department_id=None,
        location_id=None,
        room_id=None,
    ):
        return SimpleNamespace(
            role=role,
            department_id=department_id,
            location_id=location_id,
            room_id=room_id,
        )

    def make_user(self, *, active_role=None):
        return SimpleNamespace(
            active_role=active_role,
        )

    def make_request(self, *, user=None):
        return SimpleNamespace(
            user=user,
        )

    def make_view(self, *, public_id=None):
        kwargs = {}

        if public_id is not None:
            kwargs["public_id"] = public_id

        return SimpleNamespace(
            kwargs=kwargs,
        )

    def make_room(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_returns_false_without_active_role(
        self,
        mock_can_access_room,
    ):
        permission = RoomContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=None),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_room.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_returns_false_when_hierarchy_denies_room_access(
        self,
        mock_can_access_room,
    ):
        mock_can_access_room.return_value = False

        active_role = self.make_role_assignment(
            "LOCATION_VIEWER",
            location_id=1,
        )
        permission = RoomContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view()

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_room.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_returns_true_without_public_id_when_hierarchy_allows(
        self,
        mock_can_access_room,
        mock_get_object_or_404,
    ):
        mock_can_access_room.return_value = True

        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        permission = RoomContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view()

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_get_object_or_404.assert_not_called()

    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_site_admin_can_access_room_context_without_scope_check(
        self,
        mock_can_access_room,
        mock_get_object_or_404,
    ):
        mock_can_access_room.return_value = True
        room = self.make_room(id=99)
        mock_get_object_or_404.return_value = room

        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        permission = RoomContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="RM099",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_get_object_or_404.assert_called_once_with(
            Room,
            public_id="RM099",
        )

    @patch("access.permissions.sites.ScopeService.can_access_room")
    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_non_site_actor_delegates_room_scope_check(
        self,
        mock_can_access_room_hierarchy,
        mock_get_object_or_404,
        mock_can_access_room_scope,
    ):
        mock_can_access_room_hierarchy.return_value = True
        mock_can_access_room_scope.return_value = True

        room = self.make_room(id=1)
        mock_get_object_or_404.return_value = room

        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        permission = RoomContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="RM001",
        )

        self.assertTrue(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_room_scope.assert_called_once_with(
            active_role,
            room,
        )

    @patch("access.permissions.sites.ScopeService.can_access_room")
    @patch("access.permissions.sites.get_object_or_404")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_non_site_actor_denied_when_room_scope_denied(
        self,
        mock_can_access_room_hierarchy,
        mock_get_object_or_404,
        mock_can_access_room_scope,
    ):
        mock_can_access_room_hierarchy.return_value = True
        mock_can_access_room_scope.return_value = False

        room = self.make_room(id=2)
        mock_get_object_or_404.return_value = room

        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        permission = RoomContextPermission()
        request = self.make_request(
            user=self.make_user(active_role=active_role),
        )
        view = self.make_view(
            public_id="RM002",
        )

        self.assertFalse(
            permission.has_permission(
                request,
                view,
            )
        )

        mock_can_access_room_scope.assert_called_once_with(
            active_role,
            room,
        )