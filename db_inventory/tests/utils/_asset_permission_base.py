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

ROLE_MATRIX = {
    "ROOM_VIEWER": {
        "GET_in": 200,
        "GET_out": 403,
        "POST_in": 403,
        "POST_out": 403,
        "DELETE_in": 403,
    },
    "ROOM_CLERK": {
        "GET_in": 200,
        "GET_out": 403,
        "POST_in": 201,
        "POST_out": 403,
        "DELETE_in": 403,
    },
    "ROOM_ADMIN": {
        "GET_in": 200,
        "GET_out": 403,
        "POST_in": 201,
        "POST_out": 403,
        "DELETE_in": 204,
    },
    "LOCATION_ADMIN": {
        "GET_in": 200,
        "GET_out": 403,
        "POST_in": 201,
        "POST_out": 403,
        "DELETE_in": 204,
    },
    "DEPARTMENT_ADMIN": {
        "GET_in": 200,
        "GET_out": 403,
        "POST_in": 201,
        "POST_out": 403,
        "DELETE_in": 204,
    },
    "SITE_ADMIN": {
        "GET_in": 200,
        "GET_out": 200,
        "POST_in": 201,
        "POST_out": 201,
        "DELETE_in": 204,
    },
}

class AssetPermissionTestBase(APITestCase):
    asset_url_name = None        # e.g. "equipment-list"
    asset_detail_url_name = None # e.g. "equipment-detail"
    asset_factory = None         # callable to create asset

    def setUp(self):
        self._setup_locations()
        self._setup_users()

    # -------------------------
    # Core test runner
    # -------------------------

    def _assert(self, response, expected):
        self.assertEqual(
            response.status_code,
            expected,
            f"Expected {expected}, got {response.status_code}"
        )

    def _test_role(self, user, role_name):
        expectations = ROLE_MATRIX[role_name]

        self.client.force_authenticate(user)

        # GET in-scope
        resp = self.client.get(self._detail_url(self.asset_in_scope))
        self._assert(resp, expectations["GET_in"])

        # GET out-of-scope
        resp = self.client.get(self._detail_url(self.asset_out_scope))
        self._assert(resp, expectations["GET_out"])

        # POST in-scope
        resp = self.client.post(
            self._list_url(),
            self._post_payload(self.room_in_scope),
            format="json",
        )
        self._assert(resp, expectations["POST_in"])

        # POST out-of-scope
        resp = self.client.post(
            self._list_url(),
            self._post_payload(self.room_out_scope),
            format="json",
        )
        self._assert(resp, expectations["POST_out"])

        # DELETE in-scope
        resp = self.client.delete(self._detail_url(self.asset_in_scope))
        self._assert(resp, expectations["DELETE_in"])

    # -------------------------
    # URL helpers
    # -------------------------

    def _list_url(self):
        return reverse(self.asset_url_name)

    def _detail_url(self, asset):
        return reverse(
            self.asset_detail_url_name,
            kwargs={"public_id": asset.public_id},
        )

    # -------------------------
    # Override points
    # -------------------------

    def _post_payload(self, room):
        raise NotImplementedError