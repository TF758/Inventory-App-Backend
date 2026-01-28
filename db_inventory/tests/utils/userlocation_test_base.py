from rest_framework.test import APITestCase, APIClient
from django.urls import reverse

from db_inventory.factories import AdminUserFactory, DepartmentFactory, LocationFactory, RoomFactory, UserFactory
from db_inventory.models.roles import RoleAssignment

class UserLocationPermissionTestBase(APITestCase):
    """
    Shared fixtures for UserLocation permission tests.

    - Uses setUpTestData for static hierarchy + role setup (fast).
    - Subclasses should create per-test UserLocation rows in setUp(),
      and authenticate the correct user for the role being tested.
    """
    __test__ = False

    @classmethod
    def setUpTestData(cls):
        # -----------------------------
        # Hierarchy (static fixtures)
        # -----------------------------
        cls.department1 = DepartmentFactory()
        cls.department2 = DepartmentFactory()

        cls.location1 = LocationFactory(department=cls.department1)
        cls.location2 = LocationFactory(department=cls.department2)

        cls.room1 = RoomFactory(location=cls.location1)
        cls.room2 = RoomFactory(location=cls.location2)

        # -----------------------------
        # Users (static fixtures)
        # -----------------------------
        cls.site_admin = AdminUserFactory()
        cls.dept_admin = UserFactory()
        cls.location_admin = UserFactory()
        cls.room_admin = UserFactory()

        cls.department_viewer = UserFactory()
        cls.location_viewer = UserFactory()
        cls.room_viewer = UserFactory()

        # -----------------------------
        # Roles (static fixtures)
        # -----------------------------
        cls.site_admin_role = RoleAssignment.objects.create(
            user=cls.site_admin, role="SITE_ADMIN"
        )

        cls.dept_admin_role = RoleAssignment.objects.create(
            user=cls.dept_admin,
            role="DEPARTMENT_ADMIN",
            department=cls.department1,
        )

        cls.location_admin_role = RoleAssignment.objects.create(
            user=cls.location_admin,
            role="LOCATION_ADMIN",
            location=cls.location1,
        )

        cls.room_admin_role = RoleAssignment.objects.create(
            user=cls.room_admin,
            role="ROOM_ADMIN",
            room=cls.room1,
        )

        cls.department_viewer_role = RoleAssignment.objects.create(
            user=cls.department_viewer,
            role="DEPARTMENT_VIEWER",
            department=cls.department1,
        )

        cls.location_viewer_role = RoleAssignment.objects.create(
            user=cls.location_viewer,
            role="LOCATION_VIEWER",
            location=cls.location1,
        )

        cls.room_viewer_role = RoleAssignment.objects.create(
            user=cls.room_viewer,
            role="ROOM_VIEWER",
            room=cls.room1,
        )

        # -----------------------------
        # Activate roles (static fixtures)
        # -----------------------------
        for user, role in [
            (cls.site_admin, cls.site_admin_role),
            (cls.dept_admin, cls.dept_admin_role),
            (cls.location_admin, cls.location_admin_role),
            (cls.room_admin, cls.room_admin_role),
            (cls.department_viewer, cls.department_viewer_role),
            (cls.location_viewer, cls.location_viewer_role),
            (cls.room_viewer, cls.room_viewer_role),
        ]:
            user.active_role = role
            user.save()

        # -----------------------------
        # Common URLs (static fixtures)
        # -----------------------------
        cls.list_url = reverse("userlocation-list-create")

    def setUp(self):
        # Fresh client per test method (keeps isolation)
        self.client = APIClient()
