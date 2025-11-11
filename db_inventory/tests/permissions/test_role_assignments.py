from rest_framework import status
from db_inventory.models import RoleAssignment
from db_inventory.tests.utils._role_permissions_base import RoleAssignmentTestBase
from db_inventory.factories import UserFactory, DepartmentFactory, LocationFactory, RoomFactory





class TestRoleAssignmentPermissions(RoleAssignmentTestBase):
    __test__ = True  # enable test discovery

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

    def test_department_admin_crud_within_scope(self):
        """DEPARTMENT_ADMIN can manage roles within their department, cannot manage outside."""
        self.as_user(self.dep_admin)

        payload = self.make_department_role_payload(self.room_viewer, department=self.department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Department admin create")

        payload = self.make_department_role_payload(self.room_viewer, department=self.other_department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Department admin create outside scope")

    def test_location_admin_only_room_level(self):
        """LOCATION_ADMIN can only manage room-level roles in their location."""
        self.as_user(self.loc_admin)

        payload = self.make_room_role_payload(self.room_admin, room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_201_CREATED], "Location admin create room role")

        payload = self.make_room_role_payload(self.room_admin, room=self.other_room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "Location admin create room role outside scope")

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

    def test_location_admin_cannot_delete_outside_scope(self):
        """LOCATION_ADMIN cannot delete roles outside their location."""
        self.as_user(self.loc_admin)

        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_VIEWER", room=self.other_room)
        role_obj = RoleAssignment.objects.create(
            user=self.room_viewer,
            role=payload["role"],
            room=self.other_room,
            assigned_by=self.site_admin,
        )

        res = self.client.delete(self.detail_url(role_obj.public_id))
        self.assert_response_status(
            res, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
            "Location admin delete outside scope blocked"
        )
    def test_user_without_active_role_cannot_assign_roles(self):
        """A user with no active role should not be able to create or update any roles."""
        # --- Create a user with no roles ---
        no_role_user = UserFactory()
        self.as_user(no_role_user)

        # Attempt to create a department role
        payload = self.make_department_role_payload(self.room_viewer, department=self.department)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "User without active role cannot create department role")

        # Attempt to create a room role
        payload = self.make_room_role_payload(self.room_viewer, room=self.room)
        res = self.client.post(self.list_url(), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "User without active role cannot create room role")

        # --- Create a role explicitly for patch/update test ---
        existing_role = RoleAssignment.objects.create(
            user=self.room_viewer,
            role="ROOM_VIEWER",
            room=self.room,
            assigned_by=self.site_admin
        )

        # Attempt to patch/update the role
        payload = {"role": "ROOM_ADMIN"}
        res = self.client.patch(self.detail_url(existing_role.public_id), payload, format="json")
        self.assert_response_status(res, [status.HTTP_403_FORBIDDEN], "User without active role cannot update roles")


    def test_cross_hierarchy_scope_enforcement(self):
        """
        Verify that roles cannot be assigned in a nested location/room
        that belongs to a different department than the admin's scope.
        """
        # --- Create a department/location/room outside the admin's scope ---
        other_department = DepartmentFactory(name="OtherDept")
        other_location = LocationFactory(name="OtherLocation", department=other_department)
        other_room = RoomFactory(name="OtherRoom", location=other_location)

        # --- Create a department admin in the main department ---
        admin_user = UserFactory()
        dep_admin_role = RoleAssignment.objects.create(
            user=admin_user,
            role="DEPARTMENT_ADMIN",
            department=self.department,  # current main department
        )
        admin_user.active_role = dep_admin_role
        admin_user.save()

        # --- Authenticate as the admin ---
        self.as_user(admin_user)

        # Attempt to assign a room-level role in a room that belongs to other department
        payload = self.make_room_role_payload(self.room_viewer, role="ROOM_VIEWER", room=other_room)
        res = self.client.post(self.list_url(), payload, format="json")

        # Should be forbidden
        self.assert_response_status(
            res,
            [status.HTTP_403_FORBIDDEN],
            "Department admin cannot assign roles in rooms outside their department",
        )

        # Also verify no role was created
        exists = RoleAssignment.objects.filter(user=self.room_viewer, room=other_room).exists()
        self.assertFalse(exists, "Role should not have been created outside admin's department")