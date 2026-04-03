from django.test import TestCase
from rest_framework.test import APIRequestFactory, APITestCase, APIClient
from rest_framework import status
from rest_framework.reverse import reverse
from db_inventory.models import User, UserPlacement, Room, Department, Location, RoleAssignment
from db_inventory.factories import UserFactory, AdminUserFactory, DepartmentFactory, LocationFactory, RoomFactory, UserPlacementFactory
from db_inventory.tests.utils.userlocation_test_base import UserPlacementPermissionTestBase
from db_inventory.permissions.users import UserPlacementPermission
from db_inventory.viewsets.user_viewsets import UserPlacementViewSet
from db_inventory.permissions.helpers import is_in_scope
from rest_framework.request import Request


class UserPlacementPermissionMatrixTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Hierarchy
        cls.department1 = DepartmentFactory()
        cls.department2 = DepartmentFactory()

        cls.location1 = LocationFactory(department=cls.department1)
        cls.location2 = LocationFactory(department=cls.department2)

        cls.room1 = RoomFactory(location=cls.location1)
        cls.room2 = RoomFactory(location=cls.location2)

        cls.target_user = UserFactory()

        cls.ul_inside = UserPlacement.objects.create(
            user=cls.target_user,
            room=cls.room1,
        )

        cls.ul_outside = UserPlacement.objects.create(
            user=cls.target_user,
            room=cls.room2,
        )

    def _make_user_with_role(self, role, scope_field=None, scope_value=None):
        user = UserFactory()
        role_kwargs = {"user": user, "role": role}
        if scope_field:
            role_kwargs[scope_field] = scope_value

        assignment = RoleAssignment.objects.create(**role_kwargs)
        user.active_role = assignment
        user.save()
        return user

    def _assert_permission(self, user, method, obj, expected):
        factory = APIRequestFactory()
        method = method.upper()

        if method in ("POST", "PUT", "PATCH"):
            request = getattr(factory, method.lower())("/")
            request.data = {"room_id": self.room1.public_id}
        else:
            request = getattr(factory, method.lower())("/")

        request.user = user

        view = UserPlacementViewSet()
        view.action = method.lower()

        permission = UserPlacementPermission()

        if not permission.has_permission(request, view):
            self.assertFalse(expected)
            return

        result = permission.has_object_permission(request, view, obj)
        self.assertEqual(result, expected)
    
    def test_department_admin_scope(self):
        user = self._make_user_with_role(
            "DEPARTMENT_ADMIN",
            "department",
            self.department1
        )

        self._assert_permission(user, "GET", self.ul_inside, True)
        self._assert_permission(user, "GET", self.ul_outside, False)

    def test_location_admin_scope(self):
        user = self._make_user_with_role(
            "LOCATION_ADMIN",
            "location",
            self.location1
        )

        self._assert_permission(user, "GET", self.ul_inside, True)
        self._assert_permission(user, "GET", self.ul_outside, False)

    def test_room_admin_scope(self):
        user = self._make_user_with_role(
            "ROOM_ADMIN",
            "room",
            self.room1
        )

        self._assert_permission(user, "GET", self.ul_inside, True)
        self._assert_permission(user, "GET", self.ul_outside, False)

    def test_department_viewer_cannot_write(self):
        user = self._make_user_with_role(
            "DEPARTMENT_VIEWER",
            "department",
            self.department1
        )

        self._assert_permission(user, "POST", self.ul_inside, False)

class UserPlacementIntegrationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.other_department = DepartmentFactory()
        cls.other_location = LocationFactory(department=cls.other_department)
        cls.other_room = RoomFactory(location=cls.other_location)

        cls.target_user = UserFactory()

        cls.admin = UserFactory()
        cls.admin_role = RoleAssignment.objects.create(
            user=cls.admin,
            role="DEPARTMENT_ADMIN",
            department=cls.department
        )
        cls.admin.active_role = cls.admin_role
        cls.admin.save()

        cls.list_url = reverse("userlocation-list-create")


    def test_admin_can_create_inside_scope(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            {
                "user_id": self.target_user.public_id,
                "room_id": self.room.public_id
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)
    
    def test_admin_cannot_create_outside_scope(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            {
                "user_id": self.target_user.public_id,
                "room_id": self.other_room.public_id
            },
            format="json"
        )

        self.assertEqual(response.status_code, 403)

class RoomAdminUserPlacementIntegrationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.other_department = DepartmentFactory()
        cls.other_location = LocationFactory(department=cls.other_department)
        cls.other_room = RoomFactory(location=cls.other_location)

        cls.target_user = UserFactory()

        cls.user_location = UserPlacement.objects.create(
            user=cls.target_user,
            room=cls.room,
        )

        cls.room_admin = UserFactory()
        cls.room_admin_role = RoleAssignment.objects.create(
            user=cls.room_admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.room_admin.active_role = cls.room_admin_role
        cls.room_admin.save()

        cls.list_url = reverse("userlocation-list-create")
        cls.detail_url = reverse(
            "userlocation-detail",
            args=[cls.user_location.public_id],
        )

    def setUp(self):
        self.client.force_authenticate(user=self.room_admin)

        # Disable side effects
        from db_inventory.viewsets.user_viewsets import UserPlacementViewSet
        UserPlacementViewSet.audit = lambda *a, **k: None
        UserPlacementViewSet.notify = lambda *a, **k: None

    # ✅ READ allowed
    def test_room_admin_can_retrieve_inside_scope(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)

  
    def test_room_admin_cannot_create(self):
        response = self.client.post(
            self.list_url,
            {
                "user_id": self.target_user.public_id,
                "room_id": self.room.public_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

   
    def test_room_admin_cannot_update(self):
        response = self.client.patch(
            self.detail_url,
            {"room_id": self.room.public_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


    def test_room_admin_cannot_delete(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 403)

class UserPlacementBoundaryIntegrationTests(APITestCase):
    """
    Integration-level edge case coverage:
    - Null room behavior
    - Scope filtering in list
    - Active role switching
    """

    @classmethod
    def setUpTestData(cls):
        # Hierarchy
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        # Users
        cls.target_user = UserFactory()
        cls.viewer = UserFactory()

        # Role
        cls.viewer_role = RoleAssignment.objects.create(
            user=cls.viewer,
            role="ROOM_VIEWER",
            room=cls.room,
        )
        cls.viewer.active_role = cls.viewer_role
        cls.viewer.save()

        # Objects
        cls.ul_valid = UserPlacement.objects.create(
            user=cls.target_user,
            room=cls.room,
        )

        cls.ul_null = UserPlacement.objects.create(
            user=cls.target_user,
            room=None,
        )

        cls.list_url = reverse("userlocation-list-create")
        cls.detail_valid = reverse(
            "userlocation-detail",
            args=[cls.ul_valid.public_id],
        )
        cls.detail_null = reverse(
            "userlocation-detail",
            args=[cls.ul_null.public_id],
        )

    def setUp(self):
        self.client.force_authenticate(user=self.viewer)

        # Disable side effects
        from db_inventory.viewsets.user_viewsets import UserPlacementViewSet
        UserPlacementViewSet.audit = lambda *a, **k: None
        UserPlacementViewSet.notify = lambda *a, **k: None

    # -------------------------
    # Null room blocked
    # -------------------------

    def test_null_room_object_is_forbidden(self):
        response = self.client.get(self.detail_null)
        self.assertEqual(response.status_code, 403)

    def test_null_room_not_listed(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        ids = [ul["public_id"] for ul in response.data]
        self.assertIn(self.ul_valid.public_id, ids)
        self.assertNotIn(self.ul_null.public_id, ids)

    # -------------------------
    # Active role switching
    # -------------------------

    def test_active_role_switch_invalidates_scope(self):
        # Confirm initial access
        response = self.client.get(self.detail_valid)
        self.assertEqual(response.status_code, 200)

        # Move role outside scope
        other_department = DepartmentFactory()
        other_location = LocationFactory(department=other_department)
        other_room = RoomFactory(location=other_location)

        new_role = RoleAssignment.objects.create(
            user=self.viewer,
            role="ROOM_ADMIN",
            room=other_room,
        )

        self.viewer.active_role = new_role
        self.viewer.save()

        response = self.client.get(self.detail_valid)
        self.assertEqual(response.status_code, 403)