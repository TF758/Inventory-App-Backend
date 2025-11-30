from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from db_inventory.models import User, RoleAssignment, Department, Location, Room
from db_inventory.factories import AdminUserFactory, DepartmentFactory, LocationFactory, RoomFactory
import uuid

class FullUserCreateAPITest(APITestCase):

    def setUp(self):
        # --- Admin user ---
        self.admin = AdminUserFactory()
        self.client.force_login(self.admin)

        # Ensure admin has SITE_ADMIN role
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.admin,
            role="SITE_ADMIN",
            department=None,
            location=None,
            room=None,
            assigned_by=self.admin
        )
        self.admin.active_role = self.site_admin_role
        self.admin.save()

        # --- Department / Location / Room ---
        self.department = DepartmentFactory(name = "IT Department")
        self.department.save()
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.location.save()
        self.room = RoomFactory(location=self.location , name="Server Room")
        self.room.save()

        # Endpoint
        self.url = reverse("create-full-user")

    def test_create_full_user(self):
        # Payload uses public_id
        payload = {
            "user": {
                "email": "alice@example.com",
                "fname": "Alice",
                "lname": "Smith",
                "job_title": "Asset Manager",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": self.room.public_id,  
            "role": {
                "role": "DEPARTMENT_ADMIN",
                "department": self.department.public_id,
                "location": None,
                "room": None
            }
        }
   
        response = self.client.post(self.url, payload, format="json")

        # --- Assertions ---
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data

        # User
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], "alice@example.com")

        # User Location
        user_location_data = data["user_location"]
        self.assertIsNotNone(user_location_data)
        self.assertIn("public_id", user_location_data)
        self.assertEqual(user_location_data["public_id"], self.room.userlocation_set.first().public_id)

        # Role assignment
        self.assertIn("role_assignment", data)
        self.assertEqual(data["role_assignment"]["role"], "DEPARTMENT_ADMIN")
        self.assertEqual(data["role_assignment"]["department"], self.department.public_id)



class DepartmentAdminUserCreateAPITest(APITestCase):

    def setUp(self):
        # --- Create department ---
        self.department = DepartmentFactory(name="IT Department")
        self.department.save()

        # --- Create department admin user ---
        self.dept_admin = User.objects.create_user(
            email="deptadmin@example.com",
            password="StrongP@ssw0rd!",
            fname="Dept",
            lname="Admin",
            job_title="Department Manager",
            is_active=True
        )

        # --- Assign DEPARTMENT_ADMIN role to department admin ---
        self.dept_admin_role = RoleAssignment.objects.create(
            user=self.dept_admin,
            role="DEPARTMENT_ADMIN",
            department=self.department,   # restrict to this department
            location=None,
            room=None,
            assigned_by=self.dept_admin
        )
        self.dept_admin.active_role = self.dept_admin_role
        self.dept_admin.save()

        # --- Force login as department admin ---
        self.client.force_login(self.dept_admin)

        # --- Create Location & Room inside the department ---
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.location.save()
        self.room = RoomFactory(location=self.location, name="Server Room")
        self.room.save()

        # --- Endpoint to create full user ---
        self.url = reverse("create-full-user")

    def test_create_user_as_department_admin(self):
        # Payload for new user
        payload = {
            "user": {
                "email": "bob@example.com",
                "fname": "Bob",
                "lname": "Johnson",
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

        # --- User ---
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], "bob@example.com")

        # --- User Location ---
        user_location_data = data.get("user_location")
        self.assertIsNotNone(user_location_data)
        self.assertIn("public_id", user_location_data)

        # Match the created UserLocation
        actual_ul = self.room.userlocation_set.first()
        self.assertEqual(user_location_data["public_id"], actual_ul.public_id)

        # --- Role assignment ---
        self.assertIn("role_assignment", data)
        self.assertEqual(data["role_assignment"]["role"], "ROOM_ADMIN")
        self.assertIsNone(data["role_assignment"]["department"])

    def test_dept_admin_cannot_create_user_outside_their_department(self):
        """
        Department Admin should NOT be able to create a user
        in a room that belongs to another department.
        """

        # --- Create a different department ---
        other_department = DepartmentFactory(name="HR Department")
        other_department.save()

        # --- Create location + room OUTSIDE admin's department ---
        other_location = LocationFactory(department=other_department, name="HR Office")
        other_location.save()

        other_room = RoomFactory(location=other_location, name="Conf Room")
        other_room.save()

        # --- Payload attempts to use other_room (NOT allowed) ---
        payload = {
            "user": {
                "email": "outsider@example.com",
                "fname": "Out",
                "lname": "Sider",
                "job_title": "HR Staff",
                "is_active": True,
                "password": "StrongP@ssw0rd!",
                "confirm_password": "StrongP@ssw0rd!"
            },
            "user_location": other_room.public_id,  # room in WRONG department
            "role": {
                "role": "ROOM_ADMIN",
                "department": other_department.public_id,  # trying to set foreign dept
                "location": None,
                "room": other_room.public_id
            }
        }

        response = self.client.post(self.url, payload, format="json")

        # Ensure forbidden / invalid
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

        # Inspect error message to ensure it's scope related
        self.assertTrue(
            "outside your department" in str(response.data).lower()
            or "permission" in str(response.data).lower()
            or "not allowed" in str(response.data).lower()
        )

class LocationAdminUserCreateAPITest(APITestCase):

    def setUp(self):
        # --- Departments ---
        self.department = DepartmentFactory(name="IT Department")
        self.department.save()
        self.other_department = DepartmentFactory(name="HR Department")
        self.other_department.save()

        # --- Locations ---
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.location.save()
        self.other_location = LocationFactory(department=self.other_department, name="HR Office")
        self.other_location.save()

        # --- Rooms ---
        self.room = RoomFactory(location=self.location, name="Server Room")
        self.room.save()
        self.other_room = RoomFactory(location=self.other_location, name="Conf Room")
        self.other_room.save()

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

        # --- Endpoint ---
        self.url = reverse("create-full-user")

    def test_location_admin_can_create_user_in_location(self):
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
                "location": self.location.public_id,
                "room": self.room.public_id
            }
        }
        self.client.force_login(self.location_admin)
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_location_admin_cannot_create_user_outside_location(self):
        payload = {
            "user": {
                "email": "outsider.loc@example.com",
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
                "location": self.other_location.public_id,
                "room": self.other_room.public_id
            }
        }
        self.client.force_login(self.location_admin)
        response = self.client.post(self.url, payload, format="json")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])


class RoomAdminUserCreateAPITest(APITestCase):

    def setUp(self):
        # --- Create department ---
        self.department = DepartmentFactory(name="IT Department")
        self.department.save()

        # --- Create Location & Room ---
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.location.save()
        self.room = RoomFactory(location=self.location, name="Server Room")
        self.room.save()

        # --- Create Room Admin user ---
        self.room_admin = User.objects.create_user(
            email="roomadmin@example.com",
            password="StrongP@ssw0rd!",
            fname="Room",
            lname="Admin",
            job_title="Room Manager",
            is_active=True
        )

        # --- Assign ROOM_ADMIN role ---
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

        # --- Force login as room admin ---
        self.client.force_login(self.room_admin)

        # --- Endpoint ---
        self.url = reverse("create-full-user")

    def test_room_admin_can_create_user_in_room(self):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertEqual(data["user"]["email"], "alice.room@example.com")
        self.assertEqual(data["role_assignment"]["role"], "ROOM_CLERK")
        self.assertEqual(data["role_assignment"]["room"], self.room.public_id)

    def test_room_admin_cannot_create_user_outside_room(self):
        # --- Create a new room outside admin's room ---
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
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])
        self.assertTrue(
            "outside your department" in str(response.data).lower() or
            "permission" in str(response.data).lower() or
            "not allowed" in str(response.data).lower()
        )