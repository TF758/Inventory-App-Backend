from rest_framework import status
from db_inventory.models import RoleAssignment
from db_inventory.tests.utils._role_permissions_base import RoleAssignmentTestBase
from db_inventory.factories import UserFactory, DepartmentFactory, LocationFactory, RoomFactory


class TestRoleAssignmentPermissions(RoleAssignmentTestBase):
    __test__ = True  # enable test discovery

    # ----------------------
    # SETUP
    # ----------------------
    def setUp(self):
        super().setUp()
        # Ensure ROOM_ADMIN has permission in the room used in tests
        RoleAssignment.objects.update_or_create(
            user=self.room_admin,
            room=self.room,
            defaults={"role": "ROOM_ADMIN"}
        )

        # Ensure target user has no conflicting roles in the room
        RoleAssignment.objects.filter(user=self.room_viewer, room=self.room).delete()

    # ----------------------
    # ROOM-LEVEL ROLE TESTS
    # ----------------------

    def test_room_admin_only_viewer_clerk(self):
        """ROOM_ADMIN can assign ROOM_CLERK or ROOM_VIEWER in same room only."""
        self.as_user(self.room_admin)

        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_VIEWER", room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Room admin create viewer role")

        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_ADMIN", room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Room admin create higher role")

        payload = self.make_room_role_payload(self.room_viewer, room=self.other_room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Room admin create role outside room")

    def test_room_admin_cannot_escalate_role_via_update(self):
        """ROOM_ADMIN cannot escalate a user's role via PATCH."""
        self.as_user(self.room_admin)

        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_VIEWER", room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Room admin create viewer role")

        role_obj = (
            RoleAssignment.objects.filter(user=self.room_viewer, role="ROOM_VIEWER", room=self.room)
            .first()
        )
        self.assertIsNotNone(role_obj, "Expected a room viewer role to exist")

        payload = {"role": "ROOM_ADMIN"}
        res = self.client.patch(self.detail_url(role_obj.public_id), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Room admin cannot escalate role")

    # ----------------------
    # LOCATION-LEVEL ROLE TESTS
    # ----------------------

    def test_location_admin_only_room_level(self):
        """LOCATION_ADMIN can only manage room-level roles in their location."""
        self.as_user(self.loc_admin)

        payload = self.make_room_role_payload(self.room_admin, room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Location admin create room role")

        payload = self.make_room_role_payload(self.room_admin, room=self.other_room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Location admin create room role outside scope")

    def test_location_admin_cannot_assign_or_escalate_department_roles(self):
        """LOCATION_ADMIN cannot create or escalate users to department-level or higher roles."""
        self.as_user(self.loc_admin)

        # --- CREATION TESTS ---
        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_ADMIN", room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Location admin create room admin")

        payload = {
            "user": self.room_viewer.public_id,
            "role": "LOCATION_VIEWER",
            "location": self.location.public_id,
            "department": None,
            "room": None,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Location admin create location viewer")

        role_obj = RoleAssignment.objects.filter(
            user=self.room_viewer, role="LOCATION_VIEWER", location=self.location
        ).first()
        self.assertIsNotNone(role_obj, "Expected location viewer role to exist")

        # Forbidden creations
        for role in ["DEPARTMENT_VIEWER", "DEPARTMENT_ADMIN", "SITE_ADMIN"]:
            payload["role"] = role
            if role != "DEPARTMENT_VIEWER":
                payload["department"] = self.department.public_id
                payload["location"] = None
            res = self.client.post(self.list_url(), payload, format="json")
            self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], f"Location admin cannot create {role.lower()}")

        # --- UPDATE / PATCH ESCALATION TESTS ---
        for role in ["DEPARTMENT_VIEWER", "DEPARTMENT_ADMIN", "SITE_ADMIN"]:
            patch_payload = {"role": role, "department": self.department.public_id}
            res = self.client.patch(self.detail_url(role_obj.public_id), patch_payload, format="json")
            self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], f"Location admin cannot escalate to {role.lower()}")

    def test_location_admin_cannot_delete_outside_scope(self):
        """LOCATION_ADMIN cannot delete roles outside their location."""
        self.as_user(self.loc_admin)

        role_obj = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="ROOM_VIEWER",
            room=self.other_room,
            assigned_by=self.site_admin,
        )

        res = self.client.delete(self.detail_url(role_obj.public_id))
        self.assert_response_status(
            res, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
            "Location admin delete outside scope blocked"
        )

    def test_location_admin_cannot_patch_scope_outside_location(self):
        """LOCATION_ADMIN cannot change a role's room to a room outside their location."""
        self.as_user(self.loc_admin)

        role_obj = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="ROOM_ADMIN",
            room=self.room,
            assigned_by=self.site_admin,
        )

        patch_payload = {"room": self.other_room.public_id}
        res = self.client.patch(self.detail_url(role_obj.public_id), patch_payload, format="json")
        self.assert_response_status(
            res,
            [status.HTTP_403_FORBIDDEN],
            "Location admin cannot move room-level role to another location"
        )

    # ----------------------
    # DEPARTMENT-LEVEL ROLE TESTS
    # ----------------------

    def test_department_admin_crud_within_scope(self):
        """DEPARTMENT_ADMIN can manage roles within their department, cannot manage outside."""
        self.as_user(self.dep_admin)

        payload = self.make_department_role_payload(self.room_viewer, department=self.department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Department admin create")

        payload = self.make_department_role_payload(self.room_viewer, department=self.other_department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Department admin create outside scope")

    def test_department_admin_cannot_assign_or_escalate_to_site_admin(self):
        """DEPARTMENT_ADMIN cannot create or escalate users to SITE_ADMIN."""
        self.as_user(self.dep_admin)

        # --- CREATION: SITE_ADMIN forbidden ---
        payload = {
            "user": self.room_viewer.public_id,
            "role": "SITE_ADMIN",
            "department": None,
            "location": None,
            "room": None,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Dept admin should NOT be able to create site admin")

        # --- Setup normal department role ---
        payload = {
            "user": self.room_viewer.public_id,
            "role": "DEPARTMENT_VIEWER",
            "department": self.department.public_id,
            "location": None,
            "room": None,
        }
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Dept admin should be able to create department viewer")

        role_obj = RoleAssignment.objects.filter(
            user=self.room_viewer,
            role="DEPARTMENT_VIEWER",
            department=self.department,
        ).first()
        self.assertIsNotNone(role_obj, "Expected department viewer role to exist")

        # --- UPDATE: escalation to SITE_ADMIN forbidden ---
        res = self.client.patch(
            self.detail_url(role_obj.public_id),
            {"role": "SITE_ADMIN"},
            format="json"
        )
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Dept admin should NOT be able to escalate to site admin")

    def test_department_admin_can_downgrade_role_within_department(self):
        """DEPARTMENT_ADMIN can downgrade a user's role within their department."""
        self.as_user(self.dep_admin)

        role_obj = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="DEPARTMENT_ADMIN",
            department=self.department,
            assigned_by=self.site_admin,
        )

        patch_payload = {"role": "DEPARTMENT_VIEWER"}
        res = self.client.patch(self.detail_url(role_obj.public_id), patch_payload, format="json")
        self.assert_response_status(res, [status.HTTP_200_OK], "Department admin should be able to downgrade roles within their department")

    # ----------------------
    # SITE-LEVEL ROLE TESTS
    # ----------------------

    def test_site_admin_full_access(self):
        """SITE_ADMIN can list, create, update, delete roles anywhere."""
        self.as_user(self.site_admin)

        payload = self.make_department_role_payload(self.room_viewer, department=self.department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Site admin create department role")
        role_obj = RoleAssignment.objects.get(user=self.room_viewer, role="DEPARTMENT_VIEWER")

        payload = {"role": "LOCATION_ADMIN", "location": self.location.public_id, "department": None, "room": None}
        res = self.client.patch(self.detail_url(role_obj.public_id), payload, format="json")
        self.assert_response_status(res, [status.HTTP_200_OK], "Site admin update to location role")

        res = self.client.delete(self.detail_url(role_obj.public_id))
        self.assert_response_status(res, [status.HTTP_204_NO_CONTENT], "Site admin delete role")

    # ----------------------
    # EDGE / INVALID CASES
    # ----------------------

    def test_prevent_duplicate_role_assignment(self):
        """A user cannot have duplicate role assignments with the same scope."""
        self.as_user(self.dep_admin)

        payload = self.make_department_role_payload(self.room_viewer, department=self.department)
        res1 = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res1, [status.HTTP_201_CREATED], "First role assignment allowed")

        res2 = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res2, [status.HTTP_400_BAD_REQUEST], "Duplicate role assignment blocked")

        roles = RoleAssignment.objects.filter(
            user=self.room_viewer, role="DEPARTMENT_VIEWER", department=self.department
        )
        self.assertEqual(roles.count(), 1, "Duplicate role should not have been created")

    def test_invalid_scope_combination(self):
        """Role should not accept conflicting scope fields."""
        self.as_user(self.site_admin)

        payload = {
            "user": self.room_viewer.public_id,
            "role": "LOCATION_ADMIN",
            "location": self.location.public_id,
            "room": self.room.public_id,  # conflict
        }

        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_400_BAD_REQUEST], "Invalid scope combination blocked")

    def test_user_without_active_role_cannot_assign_roles(self):
        """A user with no active role should not be able to create or update any roles."""
        no_role_user = UserFactory()
        self.as_user(no_role_user)

        payload = self.make_department_role_payload(self.room_viewer, department=self.department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "User without active role cannot create department role")

        payload = self.make_room_role_payload(self.room_viewer, room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "User without active role cannot create room role")

        existing_role = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="ROOM_VIEWER",
            room=self.room,
            assigned_by=self.site_admin
        )
        payload = {"role": "ROOM_ADMIN"}
        res = self.client.patch(self.detail_url(existing_role.public_id), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "User without active role cannot update roles")

    def test_cross_hierarchy_scope_enforcement(self):
        """Roles cannot be assigned in a nested location/room that belongs to a different department."""
        other_department = DepartmentFactory(name="OtherDept")
        other_location = LocationFactory(name="OtherLocation", department=other_department)
        other_room = RoomFactory(name="OtherRoom", location=other_location)

        admin_user = UserFactory()
        dep_admin_role = RoleAssignment.objects.create(
            user=admin_user,
            role="DEPARTMENT_ADMIN",
            department=self.department,
        )
        admin_user.active_role = dep_admin_role
        admin_user.save()
        self.as_user(admin_user)

        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_VIEWER", room=other_room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Department admin cannot assign roles in rooms outside their department")

        exists = RoleAssignment.objects.filter(user=self.room_viewer, room=other_room).exists()
        self.assertFalse(exists, "Role should not have been created outside admin's department")

    def test_admin_cannot_assign_role_outside_scope(self):
        """Verify that an admin cannot assign a role in a room/location outside their scope."""
        self.as_user(self.loc_admin)
        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_ADMIN", room=self.other_room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Location admin cannot create room role outside their location")
