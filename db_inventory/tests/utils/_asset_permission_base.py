from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from db_inventory.models import RoleAssignment
from db_inventory.factories import (
    UserFactory,
    AdminUserFactory,
    RoomFactory,
    LocationFactory,
    DepartmentFactory,
)


class AssetPermissionTestBase:
    """
    Generic, reusable permission test base for any asset
    that uses AssetPermissionMixin.

    Subclass and define:
      - asset_factory
      - asset_name_singular
      - asset_name_plural
    """

    __test__ = False  # Prevent Django from running this base class directly
    asset_factory = None
    asset_name_singular = None
    asset_name_plural = None

    def setUp(self):
        assert self.asset_factory, "Subclasses must define asset_factory"
        assert self.asset_name_singular, "Subclasses must define asset_name_singular"
        assert self.asset_name_plural, "Subclasses must define asset_name_plural"

        self.client = APIClient()

        # ---------------------------
        # Hierarchy setup
        # ---------------------------
        self.dept = DepartmentFactory(name="Physics")
        self.other_dept = DepartmentFactory(name="Chemistry")

        self.loc = LocationFactory(name="Building A", department=self.dept)
        self.other_loc = LocationFactory(name="Building B", department=self.other_dept)

        self.room = RoomFactory(name="Lab 101", location=self.loc)
        self.other_room = RoomFactory(name="Lab 202", location=self.other_loc)

        # ---------------------------
        # Assets (one in-scope, one out-of-scope)
        # ---------------------------
        self.asset_in_scope = self.asset_factory(room=self.room)
        self.asset_out_scope = self.asset_factory(room=self.other_room)

        # ---------------------------
        # Users and role assignments
        # ---------------------------
        self.room_clerk = UserFactory()
        self.room_admin = UserFactory()
        self.loc_admin = UserFactory()
        self.dep_admin = UserFactory()
        self.site_admin = AdminUserFactory()

        self.room_clerk_role = RoleAssignment.objects.create(
            user=self.room_clerk, role="ROOM_CLERK", room=self.room
        )
        self.room_admin_role = RoleAssignment.objects.create(
            user=self.room_admin, role="ROOM_ADMIN", room=self.room
        )
        self.loc_admin_role = RoleAssignment.objects.create(
            user=self.loc_admin, role="LOCATION_ADMIN", location=self.loc
        )
        self.dep_admin_role = RoleAssignment.objects.create(
            user=self.dep_admin, role="DEPARTMENT_ADMIN", department=self.dept
        )
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.site_admin, role="SITE_ADMIN"
        )

        # Activate roles
        for user, role in [
            (self.room_clerk, self.room_clerk_role),
            (self.room_admin, self.room_admin_role),
            (self.loc_admin, self.loc_admin_role),
            (self.dep_admin, self.dep_admin_role),
            (self.site_admin, self.site_admin_role),
        ]:
            user.active_role = role
            user.save()

        self.put_data = {"name": "Updated Asset", "room": self.room.public_id}
        self.patch_data = {"name": "Patched Asset", "room": self.room.public_id}

    # URL helpers
    def list_url(self):
        return reverse(self.asset_name_plural)

    def detail_url(self, asset):
        return reverse(f"{self.asset_name_singular}-detail", args=[asset.public_id])

    # ---------------------------
    # Helper: execute full permission map
    # ---------------------------
    def _test_role_permissions(self, user, expected_results):
        self.client.force_authenticate(user=user)

        post_data = {"name": f"New {self.asset_name_singular}", "room": self.room.public_id}

        actions = {
            "GET_in": lambda: self.client.get(self.detail_url(self.asset_in_scope)),
            "GET_out": lambda: self.client.get(self.detail_url(self.asset_out_scope)),
            "POST_in": lambda: self.client.post(self.list_url(), post_data),
            "POST_out": lambda: self.client.post(
                self.list_url(), {"name": "New Out", "room": self.other_room.public_id}
            ),
            "PUT_in": lambda: self.client.put(self.detail_url(self.asset_in_scope), self.put_data),
            "PUT_out": lambda: self.client.put(self.detail_url(self.asset_out_scope), self.put_data),
            "PATCH_in": lambda: self.client.patch(self.detail_url(self.asset_in_scope), self.patch_data),
            "PATCH_out": lambda: self.client.patch(self.detail_url(self.asset_out_scope), self.patch_data),
            "DELETE_in": lambda: self.client.delete(self.detail_url(self.asset_in_scope)),
            "DELETE_out": lambda: self.client.delete(self.detail_url(self.asset_out_scope)),
        }

        for action, call in actions.items():
            response = call()
            expected_codes = expected_results.get(action, [])
            self.assertIn(
                response.status_code,
                expected_codes,
                msg=f"{action} failed for {user.active_role.role}: got {response.status_code}, expected one of {expected_codes}",
            )

    # ---------------------------
    # Expected behavior templates
    # ---------------------------
    def _expected_room_clerk(self):
        return {
            "GET_in": [200, 204],
            "GET_out": [403],
            "POST_in": [201],
            "POST_out": [403],
            "PUT_in": [403], "PUT_out": [403],
            "PATCH_in": [403], "PATCH_out": [403],
            "DELETE_in": [403], "DELETE_out": [403],
        }

    def _expected_room_admin(self):
        return {
            "GET_in": [200, 204], "GET_out": [403],
            "POST_in": [201], "POST_out": [403],
            "PUT_in": [200, 204], "PUT_out": [403],
            "PATCH_in": [200, 204], "PATCH_out": [403],
            "DELETE_in": [200, 204], "DELETE_out": [403],
        }

    def _expected_location_admin(self):
        return self._expected_room_admin()

    def _expected_department_admin(self):
        return self._expected_room_admin()

    def _expected_site_admin(self):
        # Site admin can do everything
        return {
            "GET_in": [200, 204],
            "GET_out": [200, 204],
            "POST_in": [201],
            "POST_out": [201],
            "PUT_in": [200, 204],
            "PUT_out": [200, 204],
            "PATCH_in": [200, 204],
            "PATCH_out": [200, 204],
            "DELETE_in": [200, 204],
            "DELETE_out": [200, 204],
        }

    # ---------------------------
    # Unified tests
    # ---------------------------
    def test_room_clerk(self):
        self._test_role_permissions(self.room_clerk, self._expected_room_clerk())

    def test_room_admin(self):
        self._test_role_permissions(self.room_admin, self._expected_room_admin())

    def test_location_admin(self):
        self._test_role_permissions(self.loc_admin, self._expected_location_admin())

    def test_department_admin(self):
        self._test_role_permissions(self.dep_admin, self._expected_department_admin())

    def test_site_admin(self):
        self._test_role_permissions(self.site_admin, self._expected_site_admin())
