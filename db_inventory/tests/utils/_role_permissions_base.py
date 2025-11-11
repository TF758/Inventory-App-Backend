from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from db_inventory.models import RoleAssignment
from db_inventory.factories import (
    UserFactory,
    AdminUserFactory,
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)

class RoleAssignmentTestBase(APITestCase):
    __test__ = False  # prevent test discovery for base class

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        # --------------------------------------------------------------------
        # Hierarchy Setup
        # --------------------------------------------------------------------
        cls.department = DepartmentFactory(name="Engineering")
        cls.other_department = DepartmentFactory(name="Physics")

        cls.location = LocationFactory(name="Main Lab", department=cls.department)
        cls.other_location = LocationFactory(name="Annex Lab", department=cls.other_department)

        cls.room = RoomFactory(name="Room 101", location=cls.location)
        cls.other_room = RoomFactory(name="Room 202", location=cls.other_location)

        # --------------------------------------------------------------------
        # Users Setup
        # --------------------------------------------------------------------
        cls.room_viewer = UserFactory()
        cls.room_admin = UserFactory()
        cls.loc_admin = UserFactory()
        cls.dep_admin = UserFactory()
        cls.site_admin = AdminUserFactory()

        # --------------------------------------------------------------------
        # Roles Setup
        # --------------------------------------------------------------------
        cls.room_viewer_role = RoleAssignment.objects.create(
            user=cls.room_viewer,
            role="ROOM_VIEWER",
            room=cls.room,
        )
        cls.room_admin_role = RoleAssignment.objects.create(
            user=cls.room_admin,
            role="ROOM_ADMIN",
            room=cls.room,
        )
        cls.loc_admin_role = RoleAssignment.objects.create(
            user=cls.loc_admin,
            role="LOCATION_ADMIN",
            location=cls.location,
        )
        cls.dep_admin_role = RoleAssignment.objects.create(
            user=cls.dep_admin,
            role="DEPARTMENT_ADMIN",
            department=cls.department,
        )
        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin,
            role="SITE_ADMIN",
        )

        # --------------------------------------------------------------------
        # Activate each user's role directly
        # --------------------------------------------------------------------
        for user, role in [
            (cls.room_viewer, cls.room_viewer_role),
            (cls.room_admin, cls.room_admin_role),
            (cls.loc_admin, cls.loc_admin_role),
            (cls.dep_admin, cls.dep_admin_role),
            (cls.site_admin, cls.site_admin_role),
        ]:
            user.active_role = role
            user.save()

    # ------------------------------------------------------------------------
    # URL Helpers
    # ------------------------------------------------------------------------
    def list_url(self):
        return reverse("role-assignment-list-create")

    def detail_url(self, role_assignment):
        public_id = getattr(role_assignment, "public_id", role_assignment)
        return reverse("role-detail", args=[public_id])

    # ------------------------------------------------------------------------
    # Authentication Helpers
    # ------------------------------------------------------------------------
    def as_user(self, user):
        self.client.force_authenticate(user=user)

    # ------------------------------------------------------------------------
    # Assertion Helpers
    # ------------------------------------------------------------------------
    def assert_response_status(self, response, expected_statuses, action_desc=""):
        self.assertIn(
            response.status_code,
            expected_statuses,
            msg=f"{action_desc} → got {response.status_code}, expected one of {expected_statuses}",
        )

    # ------------------------------------------------------------------------
    # Data Builders (fixed to auto-clear irrelevant fields)
    # ------------------------------------------------------------------------
    def make_room_role_payload(self, user, role="ROOM_CLERK", room=None):
        """Room roles must have room only, no location/department."""
        return {
            "user": user.public_id,
            "role": role,
            "room": (room or self.room).public_id,
            "location": None,
            "department": None,
        }

    def make_location_role_payload(self, user, role="LOCATION_VIEWER", location=None):
        """Location roles must have location only, no room/department."""
        return {
            "user": user.public_id,
            "role": role,
            "location": (location or self.location).public_id,
            "room": None,
            "department": None,
        }

    def make_department_role_payload(self, user, role="DEPARTMENT_VIEWER", department=None):
        """Department roles must have department only, no room/location."""
        return {
            "user": user.public_id,
            "role": role,
            "department": (department or self.department).public_id,
            "room": None,
            "location": None,
        }

    def make_site_role_payload(self, user, role="SITE_ADMIN"):
        """Site roles have no room, location, or department."""
        return {
            "user": user.public_id,
            "role": role,
            "department": None,
            "location": None,
            "room": None,
        }