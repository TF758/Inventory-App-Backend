from rest_framework import status
from db_inventory.models import RoleAssignment
from db_inventory.tests.utils._role_permissions_base import RoleAssignmentTestBase
from db_inventory.factories import UserFactory, DepartmentFactory, LocationFactory, RoomFactory
from rest_framework import status
from db_inventory.models import RoleAssignment
from db_inventory.tests.utils._role_permissions_base import RoleAssignmentTestBase
from db_inventory.factories import UserFactory
from db_inventory.permissions.constants import ROLE_HIERARCHY


class TestRoleAssignmentPermissions(RoleAssignmentTestBase):
    __test__ = True

    # ----------------------
    # SETUP
    # ----------------------
    def setUp(self):
        super().setUp()

        # Ensure ROOM_ADMIN role exists for acting user
        RoleAssignment.objects.update_or_create(
            user=self.room_admin,
            room=self.room,
            defaults={"role": "ROOM_ADMIN", "assigned_by": self.site_admin}
        )

        # Ensure clean slate for target user
        RoleAssignment.objects.filter(user=self.room_viewer).delete()

    # ----------------------
    # ROOM ADMIN
    # ----------------------

    def test_room_admin_only_viewer_or_clerk(self):
        """ROOM_ADMIN can assign ROOM_VIEWER / ROOM_CLERK only."""
        self.as_user(self.room_admin)

        # Allowed
        payload = self.make_room_role_payload(
            self.room_viewer, role="ROOM_VIEWER", room=self.room
        )
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED])

        # Forbidden escalation
        payload = self.make_room_role_payload(
            self.room_viewer, role="ROOM_ADMIN", room=self.room
        )
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

    def test_room_admin_cannot_patch_escalate(self):
        """ROOM_ADMIN cannot escalate roles via PATCH."""
        self.as_user(self.room_admin)

        role_obj = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="ROOM_VIEWER",
            room=self.room,
            assigned_by=self.site_admin,
        )

        res = self.client.patch(
            self.detail_url(role_obj.public_id),
            {"role": "ROOM_ADMIN"},
            format="json"
        )
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

    # ----------------------
    # LOCATION ADMIN
    # ----------------------

    def test_location_admin_assignment_rules(self):
        """LOCATION_ADMIN can assign location + room roles only."""
        self.as_user(self.loc_admin)

        # Allowed room role
        payload = self.make_room_role_payload(
            self.room_viewer, role="ROOM_ADMIN", room=self.room
        )
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED])

        # Allowed location viewer
        payload = {
            "user": self.room_viewer.public_id,
            "role": "LOCATION_VIEWER",
            "location": self.location.public_id,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED])

    def test_location_admin_cannot_assign_department_roles(self):
        """LOCATION_ADMIN cannot assign or escalate to department or site roles."""
        self.as_user(self.loc_admin)

        # Invalid role/scope → serializer (400)
        payload = {
            "user": self.room_viewer.public_id,
            "role": "DEPARTMENT_VIEWER",
            "location": self.location.public_id,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_400_BAD_REQUEST])

        # Valid shape but forbidden authority → permission (403)
        payload = {
            "user": self.room_viewer.public_id,
            "role": "DEPARTMENT_ADMIN",
            "department": self.department.public_id,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

    def test_location_admin_cannot_assign_department_roles(self):
        """LOCATION_ADMIN cannot assign or escalate to department or site roles."""
        self.as_user(self.loc_admin)

        payload = {
            "user": self.room_viewer.public_id,
            "role": "DEPARTMENT_VIEWER",
            "location": self.location.public_id,
        }

        res = self.client.post(self.list_url(), payload, format="json")

        # Authority failure → 403
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

        # ----------------------
        # DEPARTMENT ADMIN
    # ----------------------

    def test_department_admin_can_manage_lower_roles_only(self):
        """DEPARTMENT_ADMIN can manage roles below them within department."""
        self.as_user(self.dep_admin)

        role_obj = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="DEPARTMENT_VIEWER",
            department=self.department,
            assigned_by=self.site_admin,
        )

        res = self.client.patch(
            self.detail_url(role_obj.public_id),
            {
                "role": "ROOM_VIEWER",
                "room": self.room.public_id,  # <-- REQUIRED
            },
            format="json"
        )
        self.assert_response_status(res, [status.HTTP_200_OK])

    def test_department_admin_cannot_see_or_modify_peer_admin(self):
        """Peer DEPARTMENT_ADMIN roles are invisible."""
        self.as_user(self.dep_admin)

        peer = RoleAssignment.objects.create(
            user=UserFactory(),
            role="DEPARTMENT_ADMIN",
            department=self.department,
            assigned_by=self.site_admin,
        )

        res = self.client.patch(
            self.detail_url(peer.public_id),
            {"role": "DEPARTMENT_VIEWER"},
            format="json"
        )
        self.assert_response_status(res, [status.HTTP_404_NOT_FOUND])

    def test_department_admin_cannot_assign_site_admin(self):
        """DEPARTMENT_ADMIN cannot assign SITE_ADMIN."""
        self.as_user(self.dep_admin)

        payload = {
            "user": self.room_viewer.public_id,
            "role": "SITE_ADMIN",
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

    # ----------------------
    # SITE ADMIN
    # ----------------------

    def test_site_admin_full_control(self):
        """SITE_ADMIN can create, update, delete any role."""
        self.as_user(self.site_admin)

        # CREATE
        payload = {
            "user": self.room_viewer.public_id,
            "role": "DEPARTMENT_VIEWER",
            "department": self.department.public_id,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED])

        role_obj = RoleAssignment.objects.get(user=self.room_viewer)

        # UPDATE (role + scope change, must clear old scope)
        res = self.client.patch(
            self.detail_url(role_obj.public_id),
            {
                "role": "LOCATION_ADMIN",
                "location": self.location.public_id,
                "department": None,
            },
            format="json"
        )
        self.assert_response_status(res, [status.HTTP_200_OK])

        # DELETE
        res = self.client.delete(self.detail_url(role_obj.public_id))
        self.assert_response_status(res, [status.HTTP_204_NO_CONTENT])

    # ----------------------
    # VIEWERS / NO ROLE
    # ----------------------

    def test_viewer_cannot_see_or_manage_roles(self):
        """Viewer roles cannot list or manage roles."""
        self.as_user(self.room_viewer)

        res = self.client.get(self.list_url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload = self.make_room_role_payload(self.room_viewer, room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

    def test_user_without_active_role_blocked(self):
        """Users without active role cannot assign or edit roles."""
        user = UserFactory()
        self.as_user(user)

        payload = self.make_room_role_payload(self.room_viewer, room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN])

    # ----------------------
    # DATA INTEGRITY
    # ----------------------

    def test_prevent_duplicate_roles(self):
        """Duplicate role + scope assignments are blocked."""
        self.as_user(self.dep_admin)

        payload = self.make_department_role_payload(
            self.room_viewer, department=self.department
        )
        res1 = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res1, [status.HTTP_201_CREATED])

        res2 = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res2, [status.HTTP_400_BAD_REQUEST])

    def test_invalid_scope_combination(self):
        """Conflicting scope fields are rejected."""
        self.as_user(self.site_admin)

        payload = {
            "user": self.room_viewer.public_id,
            "role": "LOCATION_ADMIN",
            "location": self.location.public_id,
            "room": self.room.public_id,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_400_BAD_REQUEST])
