from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from access.permissions.sites import DepartmentPermission, LocationPermission, RoomPermission


class DepartmentPermissionTests(SimpleTestCase):
    """
    Department-level site resource permission tests.

    Covers:
        - CRUD method map
        - rename business rule
        - department object scope
    """


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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

    def make_user(
        self,
        *,
        active_role=None,
        is_authenticated=True,
    ):
        return SimpleNamespace(
            active_role=active_role,
            is_authenticated=is_authenticated,
        )

    def make_request(
        self,
        method="GET",
        *,
        user=None,
        data=None,
    ):
        return SimpleNamespace(
            method=method,
            user=user,
            data=data or {},
        )

    def make_view(self):
        return SimpleNamespace()

    def make_department(self, id=1):
        return SimpleNamespace(
            id=id,
        )

    # ------------------------------------------------------------------
    # Method map
    # ------------------------------------------------------------------

    def test_method_map_returns_expected_permission_codes(self):
        permission = DepartmentPermission()
        view = self.make_view()

        cases = [
            ("GET", ["departments.view"]),
            ("POST", ["departments.create"]),
            ("PUT", ["departments.update"]),
            ("PATCH", ["departments.update"]),
            ("DELETE", ["departments.delete"]),
        ]

        for method, expected in cases:
            with self.subTest(method=method):
                request = self.make_request(method)

                self.assertEqual(
                    permission.get_required_permissions(
                        request,
                        view,
                    ),
                    expected,
                )

    # ------------------------------------------------------------------
    # Object permission base behavior
    # ------------------------------------------------------------------

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_has_object_permission_returns_false_without_active_role(
        self,
        mock_can_access_department,
    ):
        permission = DepartmentPermission()
        user = self.make_user(
            active_role=None,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        department = self.make_department(id=1)

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_not_called()

    # ------------------------------------------------------------------
    # Rename business rule
    # ------------------------------------------------------------------

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_patch_name_allows_site_admin_without_hierarchy_check(
        self,
        mock_can_access_department,
    ):
        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "PATCH",
            user=user,
            data={
                "name": "New Department Name",
            },
        )
        view = self.make_view()
        department = self.make_department(id=1)

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_not_called()

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_patch_name_denies_non_site_admin_without_hierarchy_check(
        self,
        mock_can_access_department,
    ):
        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "PATCH",
            user=user,
            data={
                "name": "New Department Name",
            },
        )
        view = self.make_view()
        department = self.make_department(id=1)

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_not_called()

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_put_name_denies_non_site_admin(
        self,
        mock_can_access_department,
    ):
        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "PUT",
            user=user,
            data={
                "name": "New Department Name",
            },
        )
        view = self.make_view()
        department = self.make_department(id=1)

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_not_called()

    # ------------------------------------------------------------------
    # Normal object access
    # ------------------------------------------------------------------

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_normal_object_access_returns_false_when_hierarchy_denied(
        self,
        mock_can_access_department,
    ):
        mock_can_access_department.return_value = False

        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        department = self.make_department(id=1)

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_called_once_with(
            active_role,
        )

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_site_admin_can_access_any_department_when_hierarchy_allowed(
        self,
        mock_can_access_department,
    ):
        mock_can_access_department.return_value = True

        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        department = self.make_department(id=99)

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_called_once_with(
            active_role,
        )

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_department_actor_can_access_own_department_when_hierarchy_allowed(
        self,
        mock_can_access_department,
    ):
        mock_can_access_department.return_value = True

        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        department = self.make_department(id=1)

        self.assertTrue(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_called_once_with(
            active_role,
        )

    @patch("access.services.hierachy.HierarchyService.can_access_department")
    def test_department_actor_cannot_access_other_department_when_hierarchy_allowed(
        self,
        mock_can_access_department,
    ):
        mock_can_access_department.return_value = True

        permission = DepartmentPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        user = self.make_user(
            active_role=active_role,
        )
        request = self.make_request(
            "GET",
            user=user,
        )
        view = self.make_view()
        department = self.make_department(id=2)

        self.assertFalse(
            permission.has_object_permission(
                request,
                view,
                department,
            )
        )

        mock_can_access_department.assert_called_once_with(
            active_role,
        )

class LocationPermissionTests(SimpleTestCase):
    """
    Unit tests for LocationPermission.

    LocationPermission adds location-specific site rules:

        - POST creation requires a valid department
        - actor must be allowed to access location hierarchy
        - SITE_ADMIN may create locations in any department
        - department actors may create locations only in their department
        - only SITE_ADMIN may move a location between departments
        - normal object access is limited to department scope

    It intentionally does not retest:

        - AccessService database behavior
        - HierarchyService internals
        - serializers
        - API routing
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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

    def make_user(
        self,
        *,
        active_role=None,
        is_authenticated=True,
    ):
        return SimpleNamespace(
            active_role=active_role,
            is_authenticated=is_authenticated,
        )

    def make_request(
        self,
        method="GET",
        *,
        user=None,
        data=None,
    ):
        return SimpleNamespace(
            method=method,
            user=user,
            data=data or {},
        )

    def make_view(self):
        return SimpleNamespace()

    def make_department(
        self,
        id=1,
        public_id="DPT001",
    ):
        return SimpleNamespace(
            id=id,
            public_id=public_id,
        )

    def make_location(
        self,
        id=1,
        department_id=1,
        public_id="LOC001",
    ):
        return SimpleNamespace(
            id=id,
            department_id=department_id,
            public_id=public_id,
        )

    # ------------------------------------------------------------------
    # Method map
    # ------------------------------------------------------------------

    def test_method_map_returns_expected_permission_codes(self):
        permission = LocationPermission()
        view = self.make_view()

        cases = [
            ("GET", ["locations.view"]),
            ("POST", ["locations.create"]),
            ("PUT", ["locations.update"]),
            ("PATCH", ["locations.update"]),
            ("DELETE", ["locations.delete"]),
        ]

        for method, expected in cases:
            with self.subTest(method=method):
                request = self.make_request(method)

                self.assertEqual(
                    permission.get_required_permissions(
                        request,
                        view,
                    ),
                    expected,
                )

    # ------------------------------------------------------------------
    # POST creation validation
    # ------------------------------------------------------------------

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_when_department_missing_from_payload(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={},
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_department_filter.assert_not_called()
        mock_can_access_location.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_when_department_not_found(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True
        mock_department_filter.return_value.first.return_value = None

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "department": "DPT404",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_department_filter.assert_called_once_with(
            public_id="DPT404",
        )
        mock_can_access_location.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_without_active_role(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True
        department = self.make_department(id=1)
        mock_department_filter.return_value.first.return_value = department

        permission = LocationPermission()
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=None),
            data={
                "department": "DPT001",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_can_access_location.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_when_hierarchy_denies_location_access(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True
        mock_can_access_location.return_value = False

        department = self.make_department(id=1)
        mock_department_filter.return_value.first.return_value = department

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "department": "DPT001",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_can_access_location.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_allows_site_admin_for_any_department(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True
        mock_can_access_location.return_value = True

        department = self.make_department(id=99)
        mock_department_filter.return_value.first.return_value = department

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "department": "DPT099",
            },
        )

        self.assertTrue(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_can_access_location.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_allows_department_actor_for_own_department(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True
        mock_can_access_location.return_value = True

        department = self.make_department(id=1)
        mock_department_filter.return_value.first.return_value = department

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "department": "DPT001",
            },
        )

        self.assertTrue(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    @patch("access.permissions.sites.Department.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_denies_department_actor_for_other_department(
        self,
        mock_has_permission,
        mock_department_filter,
        mock_can_access_location,
    ):
        mock_has_permission.return_value = True
        mock_can_access_location.return_value = True

        department = self.make_department(id=2)
        mock_department_filter.return_value.first.return_value = department

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "department": "DPT002",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    # ------------------------------------------------------------------
    # Move business rule
    # ------------------------------------------------------------------

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_patch_department_move_allows_site_admin_only(
        self,
        mock_can_access_location,
    ):
        permission = LocationPermission()
        location = self.make_location(id=1, department_id=1)

        site_admin = self.make_role_assignment("SITE_ADMIN")
        department_admin = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )

        site_request = self.make_request(
            "PATCH",
            user=self.make_user(active_role=site_admin),
            data={
                "department": "DPT002",
            },
        )
        department_request = self.make_request(
            "PATCH",
            user=self.make_user(active_role=department_admin),
            data={
                "department": "DPT002",
            },
        )

        self.assertTrue(
            permission.has_object_permission(
                site_request,
                self.make_view(),
                location,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                department_request,
                self.make_view(),
                location,
            )
        )

        mock_can_access_location.assert_not_called()

    # ------------------------------------------------------------------
    # Normal object access
    # ------------------------------------------------------------------

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_normal_object_access_returns_false_when_hierarchy_denied(
        self,
        mock_can_access_location,
    ):
        mock_can_access_location.return_value = False

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        location = self.make_location(
            id=1,
            department_id=1,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                location,
            )
        )

        mock_can_access_location.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_site_admin_can_access_any_location_when_hierarchy_allowed(
        self,
        mock_can_access_location,
    ):
        mock_can_access_location.return_value = True

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        location = self.make_location(
            id=99,
            department_id=99,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                location,
            )
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_department_actor_can_access_location_inside_own_department(
        self,
        mock_can_access_location,
    ):
        mock_can_access_location.return_value = True

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        location = self.make_location(
            id=10,
            department_id=1,
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                location,
            )
        )

    @patch("access.permissions.sites.HierarchyService.can_access_location")
    def test_department_actor_cannot_access_location_outside_department(
        self,
        mock_can_access_location,
    ):
        mock_can_access_location.return_value = True

        permission = LocationPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        location = self.make_location(
            id=10,
            department_id=2,
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                location,
            )
        )

class RoomPermissionTests(SimpleTestCase):
    """
    Unit tests for RoomPermission.

    RoomPermission adds room-specific site rules:

        - POST creation requires a valid location
        - actor must be allowed to access room hierarchy
        - SITE_ADMIN may create rooms in any location
        - department actors may create rooms only in locations in their department
        - location actors may create rooms only in their location
        - only SITE_ADMIN and DEPARTMENT_ADMIN may move a room between locations
        - normal object access delegates room scope to ScopeService

    It intentionally does not retest:

        - AccessService database behavior
        - HierarchyService internals
        - ScopeService role/scope combinations
        - serializers
        - API routing
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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

    def make_user(
        self,
        *,
        active_role=None,
        is_authenticated=True,
    ):
        return SimpleNamespace(
            active_role=active_role,
            is_authenticated=is_authenticated,
        )

    def make_request(
        self,
        method="GET",
        *,
        user=None,
        data=None,
    ):
        return SimpleNamespace(
            method=method,
            user=user,
            data=data or {},
        )

    def make_view(self):
        return SimpleNamespace()

    def make_location(
        self,
        id=1,
        department_id=1,
        public_id="LOC001",
    ):
        return SimpleNamespace(
            id=id,
            department_id=department_id,
            public_id=public_id,
        )

    def make_room(
        self,
        id=1,
        location=None,
    ):
        location = location or self.make_location()

        return SimpleNamespace(
            id=id,
            location=location,
            location_id=location.id,
        )

    # ------------------------------------------------------------------
    # Method map
    # ------------------------------------------------------------------

    def test_method_map_returns_expected_permission_codes(self):
        permission = RoomPermission()
        view = self.make_view()

        cases = [
            ("GET", ["rooms.view"]),
            ("POST", ["rooms.create"]),
            ("PUT", ["rooms.update"]),
            ("PATCH", ["rooms.update"]),
            ("DELETE", ["rooms.delete"]),
        ]

        for method, expected in cases:
            with self.subTest(method=method):
                request = self.make_request(method)

                self.assertEqual(
                    permission.get_required_permissions(
                        request,
                        view,
                    ),
                    expected,
                )

    # ------------------------------------------------------------------
    # POST creation validation
    # ------------------------------------------------------------------

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_when_location_missing_from_payload(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={},
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_location_filter.assert_not_called()
        mock_can_access_room.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_when_location_not_found(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_location_filter.return_value.first.return_value = None

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC404",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_location_filter.assert_called_once_with(
            public_id="LOC404",
        )
        mock_can_access_room.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_without_active_role(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True

        location = self.make_location(id=1, department_id=1)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=None),
            data={
                "location": "LOC001",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_can_access_room.assert_not_called()

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_returns_false_when_hierarchy_denies_room_access(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = False

        location = self.make_location(id=1, department_id=1)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC001",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_can_access_room.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_allows_site_admin_for_any_location(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        location = self.make_location(id=99, department_id=99)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "SITE_ADMIN",
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC099",
            },
        )

        self.assertTrue(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

        mock_can_access_room.assert_called_once_with(
            active_role,
        )

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_allows_department_actor_for_location_inside_department(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        location = self.make_location(id=10, department_id=1)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC010",
            },
        )

        self.assertTrue(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_denies_department_actor_for_location_outside_department(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        location = self.make_location(id=10, department_id=2)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "DEPARTMENT_ADMIN",
            department_id=1,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC010",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_allows_location_actor_for_own_location(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        location = self.make_location(id=10, department_id=1)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC010",
            },
        )

        self.assertTrue(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    @patch("access.permissions.sites.HierarchyService.can_access_room")
    @patch("access.permissions.sites.Location.objects.filter")
    @patch("access.permissions.base.AccessService.has_permission")
    def test_post_denies_location_actor_for_other_location(
        self,
        mock_has_permission,
        mock_location_filter,
        mock_can_access_room,
    ):
        mock_has_permission.return_value = True
        mock_can_access_room.return_value = True

        location = self.make_location(id=11, department_id=1)
        mock_location_filter.return_value.first.return_value = location

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=10,
        )
        request = self.make_request(
            "POST",
            user=self.make_user(active_role=active_role),
            data={
                "location": "LOC011",
            },
        )

        self.assertFalse(
            permission.has_permission(
                request,
                self.make_view(),
            )
        )

    # ------------------------------------------------------------------
    # Move business rule
    # ------------------------------------------------------------------

    @patch("access.permissions.sites.ScopeService.can_access_room")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_patch_location_move_allows_site_and_department_admin_only(
        self,
        mock_can_access_room_hierarchy,
        mock_can_access_room_scope,
    ):
        permission = RoomPermission()
        room = self.make_room(id=1)

        allowed_roles = [
            self.make_role_assignment("SITE_ADMIN"),
            self.make_role_assignment(
                "DEPARTMENT_ADMIN",
                department_id=1,
            ),
        ]

        denied_roles = [
            self.make_role_assignment(
                "LOCATION_ADMIN",
                location_id=1,
            ),
            self.make_role_assignment(
                "ROOM_ADMIN",
                room_id=1,
            ),
        ]

        for active_role in allowed_roles:
            with self.subTest(role=active_role.role):
                request = self.make_request(
                    "PATCH",
                    user=self.make_user(active_role=active_role),
                    data={
                        "location": "LOC002",
                    },
                )

                self.assertTrue(
                    permission.has_object_permission(
                        request,
                        self.make_view(),
                        room,
                    )
                )

        for active_role in denied_roles:
            with self.subTest(role=active_role.role):
                request = self.make_request(
                    "PATCH",
                    user=self.make_user(active_role=active_role),
                    data={
                        "location": "LOC002",
                    },
                )

                self.assertFalse(
                    permission.has_object_permission(
                        request,
                        self.make_view(),
                        room,
                    )
                )

        mock_can_access_room_hierarchy.assert_not_called()
        mock_can_access_room_scope.assert_not_called()

    # ------------------------------------------------------------------
    # Normal object access
    # ------------------------------------------------------------------

    @patch("access.permissions.sites.ScopeService.can_access_room")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_normal_object_access_returns_false_when_hierarchy_denied(
        self,
        mock_can_access_room_hierarchy,
        mock_can_access_room_scope,
    ):
        mock_can_access_room_hierarchy.return_value = False

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        room = self.make_room(id=1)

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                room,
            )
        )

        mock_can_access_room_hierarchy.assert_called_once_with(
            active_role,
        )
        mock_can_access_room_scope.assert_not_called()

    @patch("access.permissions.sites.ScopeService.can_access_room")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_normal_object_access_returns_false_when_scope_denied(
        self,
        mock_can_access_room_hierarchy,
        mock_can_access_room_scope,
    ):
        mock_can_access_room_hierarchy.return_value = True
        mock_can_access_room_scope.return_value = False

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "ROOM_ADMIN",
            room_id=1,
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        room = self.make_room(id=2)

        self.assertFalse(
            permission.has_object_permission(
                request,
                self.make_view(),
                room,
            )
        )

        mock_can_access_room_hierarchy.assert_called_once_with(
            active_role,
        )
        mock_can_access_room_scope.assert_called_once_with(
            active_role,
            room,
        )

    @patch("access.permissions.sites.ScopeService.can_access_room")
    @patch("access.permissions.sites.HierarchyService.can_access_room")
    def test_normal_object_access_returns_true_when_hierarchy_and_scope_allowed(
        self,
        mock_can_access_room_hierarchy,
        mock_can_access_room_scope,
    ):
        mock_can_access_room_hierarchy.return_value = True
        mock_can_access_room_scope.return_value = True

        permission = RoomPermission()
        active_role = self.make_role_assignment(
            "LOCATION_ADMIN",
            location_id=1,
        )
        request = self.make_request(
            "GET",
            user=self.make_user(active_role=active_role),
        )
        room = self.make_room(id=1)

        self.assertTrue(
            permission.has_object_permission(
                request,
                self.make_view(),
                room,
            )
        )

        mock_can_access_room_hierarchy.assert_called_once_with(
            active_role,
        )
        mock_can_access_room_scope.assert_called_once_with(
            active_role,
            room,
        )