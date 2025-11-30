from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from db_inventory.models import User, RoleAssignment, Department, Location, Room, UserLocation
from db_inventory.factories import AdminUserFactory, DepartmentFactory, LocationFactory, RoomFactory
import uuid

class SiteAdminFullUserCreateTest(APITestCase):
    """Verify that SITE_ADMIN can create users anywhere"""

    def setUp(self):
        # --- Create SITE_ADMIN ---
        self.site_admin = AdminUserFactory()
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.site_admin,
            role="SITE_ADMIN",
            department=None,
            location=None,
            room=None,
            assigned_by=self.site_admin
        )
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

        self.client.force_login(self.site_admin)

        # --- Department, Location, Room ---
        self.department = DepartmentFactory(name="IT")
        self.location = LocationFactory(department=self.department, name="HQ")
        self.room = RoomFactory(location=self.location, name="Server Room")

        # --- Endpoint ---
        self.url = reverse("create-full-user")

    def test_site_admin_can_create_user_anywhere(self):
        payload = {
            "user": {
                "email": "alice.site@example.com",
                "fname": "Alice",
                "lname": "Site",
                "job_title": "Engineer",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": self.room.public_id,
            "role": {
                "role": "ROOM_ADMIN",
                "department": None,
                "location": None,
                "room": self.room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertEqual(data["user"]["email"], "alice.site@example.com")
        self.assertEqual(data["role_assignment"]["role"], "ROOM_ADMIN")
        # Fetch the UserLocation for the newly created user
        ul_instance = UserLocation.objects.get(user__email="alice.site@example.com")

        # Assert it exists and matches the expected room
        self.assertIsNotNone(ul_instance)
        self.assertEqual(ul_instance.room, self.room)


class DepartmentAdminFullUserCreateTest(APITestCase):
    """Verify that DEPARTMENT_ADMIN can create users only within their department"""

    def setUp(self):
        # --- Create Department ---
        self.department = DepartmentFactory(name="IT")
        self.department.save()
        self.other_department = DepartmentFactory(name="HR")
        self.other_department.save()

        # --- Department Admin ---
        self.dept_admin = User.objects.create_user(
            email="deptadmin@example.com",
            password="StrongP@ssw0rd!",
            fname="Dept",
            lname="Admin",
            job_title="Manager",
            is_active=True
        )
        self.dept_admin_role = RoleAssignment.objects.create(
            user=self.dept_admin,
            role="DEPARTMENT_ADMIN",
            department=self.department,
            location=None,
            room=None,
            assigned_by=self.dept_admin
        )
        self.dept_admin.active_role = self.dept_admin_role
        self.dept_admin.save()
        self.client.force_login(self.dept_admin)

        # --- Locations & Rooms ---
        self.location = LocationFactory(department=self.department, name="HQ")
        self.location.save()
        self.room = RoomFactory(location=self.location, name="Server Room")
        self.room.save()

        self.other_location = LocationFactory(department=self.other_department, name="HR Office")
        self.other_location.save()
        self.other_room = RoomFactory(location=self.other_location, name="Conf Room")
        self.other_room.save()

        # --- Endpoint ---
        self.url = reverse("create-full-user")

    def test_dept_admin_can_create_user_in_department(self):
        """Department Admin can create a user in a room within their department"""
        payload = {
            "user": {
                "email": "bob.dept@example.com",
                "fname": "Bob",
                "lname": "Dept",
                "job_title": "Technician",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": self.room.public_id,
            "role": {
                "role": "ROOM_ADMIN",
                "department": None,
                "location": None,
                "room": self.room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertEqual(data["user"]["email"], "bob.dept@example.com")
        self.assertEqual(data["role_assignment"]["role"], "ROOM_ADMIN")

        # Confirm UserLocation created correctly
        ul_instance = UserLocation.objects.get(user__email="bob.dept@example.com")
        self.assertIsNotNone(ul_instance)
        self.assertEqual(ul_instance.room, self.room)

    def test_dept_admin_cannot_create_user_outside_department(self):
        """Department Admin cannot create users in another department"""
        payload = {
            "user": {
                "email": "outsider.dept@example.com",
                "fname": "Out",
                "lname": "Sider",
                "job_title": "HR Staff",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": self.other_room.public_id,
            "role": {
                "role": "ROOM_ADMIN",
                "department": None,
                "location": None,
                "room": self.other_room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

class LocationAdminFullUserCreateTest(APITestCase):
    """Verify that LOCATION_ADMIN cannot create users via the full-user endpoint"""

    def setUp(self):
        # --- Departments ---
        self.department = DepartmentFactory(name="IT")
        self.department.save()

        # --- Locations & Rooms ---
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.location.save()
        self.room = RoomFactory(location=self.location, name="Server Room")
        self.room.save()

        # --- Location Admin user ---
        self.location_admin = User.objects.create_user(
            email="locadmin@example.com",
            password="StrongP@ssw0rd!",
            fname="Loc",
            lname="Admin",
            job_title="Location Manager",
            is_active=True
        )
        self.location_admin_role = RoleAssignment.objects.create(
            user=self.location_admin,
            role="LOCATION_ADMIN",
            department=None,
            location=self.location,
            room=None,
            assigned_by=self.location_admin
        )
        self.location_admin.active_role = self.location_admin_role
        self.location_admin.save()
        self.client.force_login(self.location_admin)

        # --- Endpoint ---
        self.url = reverse("create-full-user")

    def test_location_admin_cannot_create_user_in_location(self):
        """Location Admin cannot create users via this endpoint, even in their location"""
        payload = {
            "user": {
                "email": "alice.loc@example.com",
                "fname": "Alice",
                "lname": "Loc",
                "job_title": "Technician",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": self.room.public_id,
            "role": {
                "role": "ROOM_ADMIN",
                "department": None,
                "location": None,
                "room": self.room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_admin_cannot_create_user_outside_location(self):
        """Location Admin also cannot create users in rooms outside their location"""
        other_room = RoomFactory(location=self.location, name="Conf Room")
        other_room.save()

        payload = {
            "user": {
                "email": "outsider.loc@example.com",
                "fname": "Out",
                "lname": "Sider",
                "job_title": "Technician",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": other_room.public_id,
            "role": {
                "role": "ROOM_ADMIN",
                "department": None,
                "location": None,
                "room": other_room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class RoomAdminFullUserCreateTest(APITestCase):
    """Verify that ROOM_ADMIN cannot create users via the full-user endpoint"""

    def setUp(self):
        # --- Department ---
        self.department = DepartmentFactory(name="IT")
        self.department.save()

        # --- Location & Room ---
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.location.save()
        self.room = RoomFactory(location=self.location, name="Server Room")
        self.room.save()

        # --- Room Admin user ---
        self.room_admin = User.objects.create_user(
            email="roomadmin@example.com",
            password="StrongP@ssw0rd!",
            fname="Room",
            lname="Admin",
            job_title="Room Manager",
            is_active=True
        )
        self.room_admin_role = RoleAssignment.objects.create(
            user=self.room_admin,
            role="ROOM_ADMIN",
            department=None,
            location=None,
            room=self.room,
            assigned_by=self.room_admin
        )
        self.room_admin.active_role = self.room_admin_role
        self.room_admin.save()

        # --- Force login ---
        self.client.force_login(self.room_admin)

        # --- Endpoint ---
        self.url = reverse("create-full-user")

    def test_room_admin_cannot_create_user_in_room(self):
        """Room Admin cannot create a user in their own room"""
        payload = {
            "user": {
                "email": "alice.room@example.com",
                "fname": "Alice",
                "lname": "Room",
                "job_title": "Technician",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": self.room.public_id,
            "role": {
                "role": "ROOM_CLERK",
                "department": None,
                "location": None,
                "room": self.room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_admin_cannot_create_user_outside_room(self):
        """Room Admin cannot create a user in another room"""
        other_room = RoomFactory(location=self.location, name="Conf Room")
        other_room.save()

        payload = {
            "user": {
                "email": "outsider.room@example.com",
                "fname": "Out",
                "lname": "Sider",
                "job_title": "Technician",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": other_room.public_id,
            "role": {
                "role": "ROOM_CLERK",
                "department": None,
                "location": None,
                "room": other_room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)