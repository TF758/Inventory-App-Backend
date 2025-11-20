from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from db_inventory.models import User, RoleAssignment, Department
from db_inventory.factories import AdminUserFactory, DepartmentFactory, LocationFactory, UserFactory, RoomFactory

class UserPermissionSiteAdminTest(APITestCase):

    def setUp(self):
        # --- Create Site Admin ---
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

        # --- Target user for CRUD ---
        self.target_user = User.objects.create_user(
            email="target@example.com",
            password="StrongP@ssw0rd!",
            fname="Target",
            lname="User",
            job_title="Technician",
            is_active=True
        )

        # URLs based on ViewSet
        self.list_url = reverse("users")  # users/
        self.detail_url = reverse("user-detail", kwargs={"public_id": self.target_user.public_id})

    def test_site_admin_can_crud_users(self):
        """Site Admin should be able to GET, POST, PUT, PATCH, DELETE users"""

        # --- GET list ---
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(u["email"] == "target@example.com" for u in response.data["results"]))

        # --- GET detail ---
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "target@example.com")

        # --- POST / Create ---
        payload = {
            "email": "newuser@example.com",
            "fname": "New",
            "lname": "User",
            "job_title": "Analyst",
            "is_active": True,
            "password": "StrongP@ssw0rd!",
            "confirm_password": "StrongP@ssw0rd!"
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user_public_id = response.data["public_id"]

        # --- PUT / Update ---
        update_payload = {
            "fname": "Updated",
            "lname": "User",
            "job_title": "Analyst",
            "email": "newuser@example.com",
            "is_active": True,
            "password": "StrongP@ssw0rd!",
            "confirm_password": "StrongP@ssw0rd!"
        }
        response = self.client.put(
            reverse("user-detail", kwargs={"public_id": new_user_public_id}),
            update_payload,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fname"], "Updated")

        # --- PATCH / Partial Update ---
        patch_payload = {"lname": "Changed"}
        response = self.client.patch(
            reverse("user-detail", kwargs={"public_id": new_user_public_id}),
            patch_payload,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lname"], "Changed")

        # --- DELETE / Remove ---
        response = self.client.delete(
            reverse("user-detail", kwargs={"public_id": new_user_public_id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(public_id=new_user_public_id).exists())


class DepartmentAdminUserPermissionTest(APITestCase):

    def setUp(self):
        # Create Department
        self.department = DepartmentFactory(name="IT Department")
        self.department.save()

        # Create Department Admin
        self.dept_admin = UserFactory()
        self.dept_admin.set_password("StrongP@ssw0rd!")
        self.dept_admin.save()

        # Assign DEPARTMENT_ADMIN role
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

        # Create Location & Room in that department
        self.location = LocationFactory(department=self.department, name="Main Office")
        self.room = RoomFactory(location=self.location, name="Server Room")

        # Create a regular user to operate on
        self.user = UserFactory()
        self.user_role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            department=None,
            location=None,
            room=self.room,
            assigned_by=self.dept_admin
        )
        self.user.active_role = self.user_role
        self.user.save()

        # Login as department admin
        self.client.force_login(self.dept_admin)

        # URL endpoints
        self.user_list_url = reverse("users")
        self.user_detail_url = reverse("user-detail", kwargs={"public_id": self.user.public_id})

    def test_department_admin_crud_user(self):
        """
        Department admin should be able to GET, POST, PUT, PATCH, DELETE users
        **within their department**, but cannot touch users outside the department.
        """

        # --- GET /users/ ---
        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # --- POST /users/ (create new user) ---
        new_user_payload = {
            "email": "newuser@example.com",
            "fname": "New",
            "lname": "User",
            "job_title": "Technician",
            "is_active": True,
            "password": "StrongP@ssw0rd!",
            "confirm_password": "StrongP@ssw0rd!"
        }
        response = self.client.post(self.user_list_url, new_user_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_user_public_id = response.data["public_id"]

        # --- PUT / PATCH /users/<id>/ ---
        update_payload = {"job_title": "Updated Title"}

        put_response = self.client.put(
            reverse("user-detail", kwargs={"public_id": created_user_public_id}),
            update_payload,
            format="json"
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            reverse("user-detail", kwargs={"public_id": created_user_public_id}),
            {"job_title": "Patched Title"},
            format="json"
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # --- DELETE /users/<id>/ ---
        delete_response = self.client.delete(
            reverse("user-detail", kwargs={"public_id": created_user_public_id})
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_department_admin_cannot_crud_outside_department(self):
            # Create user outside their department
            other_department = DepartmentFactory(name="HR")
            other_location = LocationFactory(department=other_department, name="HR Office")
            other_room = RoomFactory(location=other_location, name="HR Room")

            outside_user = UserFactory()
            RoleAssignment.objects.create(
                user=outside_user,
                role="ROOM_ADMIN",
                department=None,
                location=None,
                room=other_room,
                assigned_by=self.dept_admin
            )
            outside_user.active_role = outside_user.roleassignment_set.first()
            outside_user.save()

            url = reverse("user-detail", kwargs={"public_id": outside_user.public_id})

            # PUT / PATCH / DELETE should be forbidden
            put_resp = self.client.put(url, {"fname": "Hacked"}, format="json")
            patch_resp = self.client.patch(url, {"fname": "Hacked"}, format="json")
            del_resp = self.client.delete(url)

            self.assertIn(put_resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])
            self.assertIn(patch_resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])
            self.assertIn(del_resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])