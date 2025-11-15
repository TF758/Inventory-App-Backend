from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.reverse import reverse
from db_inventory.models import User, UserLocation, Room, Department, Location, RoleAssignment
from db_inventory.factories import UserFactory, AdminUserFactory, DepartmentFactory, LocationFactory, RoomFactory, UserLocationFactory

class SiteAdminUserLocationTests(TestCase):
    def setUp(self):
        # Create a SITE_ADMIN user
        self.site_admin = AdminUserFactory()
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.site_admin,
            role="SITE_ADMIN"
        )
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

        self.client = APIClient()
        self.client.force_authenticate(user=self.site_admin)

        # Create departments, locations, rooms, and users in different scopes
        self.department1 = DepartmentFactory()
        self.department2 = DepartmentFactory()

        self.location1 = LocationFactory(department=self.department1)
        self.location2 = LocationFactory(department=self.department2)

        self.room1 = RoomFactory(location=self.location1)
        self.room2 = RoomFactory(location=self.location2)

        # Create users to assign
        self.user1 = UserFactory()
        self.user2 = UserFactory()

        # Pre-existing UserLocation objects
        self.user_location1 = UserLocationFactory(user=self.user1, room=self.room1)
        self.user_location2 = UserLocationFactory(user=self.user2, room=self.room2)

        # Reverse URLs
        self.url_list = reverse('userlocation-list-create')
        self.url_detail_ul1 = reverse('userlocation-detail', args=[self.user_location1.public_id])
        self.url_detail_ul2 = reverse('userlocation-detail', args=[self.user_location2.public_id])

    def test_site_admin_can_list_all_user_locations(self):
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        public_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.user_location1.public_id, public_ids)
        self.assertIn(self.user_location2.public_id, public_ids)

    def test_site_admin_can_retrieve_any_user_location(self):
        response = self.client.get(self.url_detail_ul1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['public_id'], self.user_location1.public_id)

    def test_site_admin_can_create_user_location_anywhere(self):
        payload = {
            "user_id": self.user1.public_id,
            "room_id": self.room2.public_id,
        }
        response = self.client.post(self.url_list, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['room_id'], self.room2.public_id)

    def test_site_admin_can_update_user_location_anywhere(self):
        payload = {"room_id": self.room2.public_id}
        response = self.client.patch(self.url_detail_ul1, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['room_id'], self.room2.public_id)

    def test_site_admin_can_delete_user_location_anywhere(self):
        response = self.client.delete(self.url_detail_ul1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserLocation.objects.filter(pk=self.user_location1.pk).exists())

class DepartmentAdminUserLocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.department1 = DepartmentFactory()
        self.department2 = DepartmentFactory()

        # Create locations and rooms
        self.location1 = LocationFactory(department=self.department1)
        self.location2 = LocationFactory(department=self.department2)
        self.room1 = RoomFactory(location=self.location1)
        self.room2 = RoomFactory(location=self.location2)

        # Create users
        self.dept_admin = UserFactory()
        self.user_in_dept = UserFactory()
        self.user_outside_dept = UserFactory()

        # Assign department admin role
        RoleAssignment.objects.create(
            user=self.dept_admin,
            role="DEPARTMENT_ADMIN",
            department=self.department1
        )
        self.dept_admin.active_role = RoleAssignment.objects.get(user=self.dept_admin)
        self.dept_admin.save()

        # Create UserLocations
        self.userlocation_in_dept = UserLocationFactory(user=self.user_in_dept, room=self.room1)
        self.userlocation_outside_dept = UserLocationFactory(user=self.user_outside_dept, room=self.room2)

        # Authenticate as dept admin
        self.client.force_authenticate(user=self.dept_admin)

        # Reverse URLs
        self.list_url = reverse('userlocation-list-create')
        self.detail_url_in = reverse('userlocation-detail', args=[self.userlocation_in_dept.public_id])
        self.detail_url_out = reverse('userlocation-detail', args=[self.userlocation_outside_dept.public_id])

    def test_dept_admin_can_list_userlocations_in_their_department(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see userlocations in their department
        returned_ids = [u['public_id'] for u in response.data]
        self.assertIn(self.userlocation_in_dept.public_id, returned_ids)
        self.assertNotIn(self.userlocation_outside_dept.public_id, returned_ids)

    def test_dept_admin_can_retrieve_userlocation_in_their_department(self):
        response = self.client.get(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dept_admin_cannot_retrieve_userlocation_outside_department(self):
        response = self.client.get(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dept_admin_can_update_userlocation_in_their_department(self):
        payload = {'room_id': self.room1.public_id, 'is_current': True}
        response = self.client.patch(self.detail_url_in, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dept_admin_cannot_update_userlocation_outside_department(self):
        payload = {'room_id': self.room2.public_id, 'is_current': True}
        response = self.client.patch(self.detail_url_out, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dept_admin_can_create_userlocation_in_their_department(self):
        new_user = UserFactory()
        payload = {
            'user_id': new_user.public_id,
            'room_id': self.room1.public_id
        }
        response = self.client.post(self.list_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['room_id'], self.room1.public_id)

    def test_dept_admin_cannot_create_userlocation_outside_department(self):
        new_user = UserFactory()
        payload = {
            'user_id': new_user.public_id,
            'room_id': self.room2.public_id
        }
        response = self.client.post(self.list_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dept_admin_can_delete_userlocation_in_their_department(self):
        response = self.client.delete(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_dept_admin_cannot_delete_userlocation_outside_department(self):
        response = self.client.delete(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LocationAdminUserLocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.department1 = DepartmentFactory()
        self.department2 = DepartmentFactory()

        # Create locations and rooms
        self.location1 = LocationFactory(department=self.department1)
        self.location2 = LocationFactory(department=self.department2)
        self.room1 = RoomFactory(location=self.location1)
        self.room2 = RoomFactory(location=self.location2)

        # Create users
        self.location_admin = UserFactory()
        self.user_in_location = UserFactory()
        self.user_outside_location = UserFactory()

        # Assign location admin role
        RoleAssignment.objects.create(
            user=self.location_admin,
            role="LOCATION_ADMIN",
            location=self.location1
        )
        self.location_admin.active_role = RoleAssignment.objects.get(user=self.location_admin)
        self.location_admin.save()

        # Create UserLocations
        self.userlocation_in_location = UserLocationFactory(user=self.user_in_location, room=self.room1)
        self.userlocation_outside_location = UserLocationFactory(user=self.user_outside_location, room=self.room2)

        # Authenticate as location admin
        self.client.force_authenticate(user=self.location_admin)

        # Reverse URLs
        self.list_url = reverse('userlocation-list-create')
        self.detail_url_in = reverse('userlocation-detail', args=[self.userlocation_in_location.public_id])
        self.detail_url_out = reverse('userlocation-detail', args=[self.userlocation_outside_location.public_id])

    def test_location_admin_can_list_userlocations_in_their_location(self):
        response = self.client.get(self.list_url)
        returned_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.userlocation_in_location.public_id, returned_ids)
        self.assertNotIn(self.userlocation_outside_location.public_id, returned_ids)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_location_admin_can_retrieve_userlocation_inside_location(self):
        response = self.client.get(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_location_admin_cannot_retrieve_userlocation_outside_location(self):
        response = self.client.get(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_admin_can_create_userlocation_inside_location(self):
        new_user = UserFactory()
        payload = {'user_id': new_user.public_id, 'room_id': self.room1.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_location_admin_cannot_create_userlocation_outside_location(self):
        new_user = UserFactory()
        payload = {'user_id': new_user.public_id, 'room_id': self.room2.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_admin_can_update_userlocation_inside_location(self):
        payload = {'room_id': self.room1.public_id}
        response = self.client.patch(self.detail_url_in, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_location_admin_cannot_update_userlocation_outside_location(self):
        payload = {'room_id': self.room2.public_id}
        response = self.client.patch(self.detail_url_out, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_admin_can_delete_userlocation_inside_location(self):
        response = self.client.delete(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_location_admin_cannot_delete_userlocation_outside_location(self):
        response = self.client.delete(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class RoomAdminUserLocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.department1 = DepartmentFactory()
        self.department2 = DepartmentFactory()

        # Create locations
        self.location1 = LocationFactory(department=self.department1)
        self.location2 = LocationFactory(department=self.department2)

        # Create rooms
        self.room1 = RoomFactory(location=self.location1)
        self.room2 = RoomFactory(location=self.location2)

        # Create users
        self.room_admin = UserFactory()
        self.user_in_room = UserFactory()
        self.user_outside_room = UserFactory()

        # Assign room admin role
        RoleAssignment.objects.create(
            user=self.room_admin,
            role="ROOM_ADMIN",
            room=self.room1
        )
        self.room_admin.active_role = RoleAssignment.objects.get(user=self.room_admin)
        self.room_admin.save()

        # Create UserLocations
        self.userlocation_in_room = UserLocationFactory(user=self.user_in_room, room=self.room1)
        self.userlocation_outside_room = UserLocationFactory(user=self.user_outside_room, room=self.room2)

        # Authenticate as room admin
        self.client.force_authenticate(user=self.room_admin)

        # URLs
        self.list_url = reverse('userlocation-list-create')
        self.detail_url_in = reverse('userlocation-detail', args=[self.userlocation_in_room.public_id])
        self.detail_url_out = reverse('userlocation-detail', args=[self.userlocation_outside_room.public_id])


    def test_room_admin_can_list_userlocations_in_their_room(self):
        response = self.client.get(self.list_url)
        returned_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.userlocation_in_room.public_id, returned_ids)
        self.assertNotIn(self.userlocation_outside_room.public_id, returned_ids)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_room_admin_can_retrieve_userlocation_inside_room(self):
        response = self.client.get(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_room_admin_cannot_retrieve_userlocation_outside_room(self):
        response = self.client.get(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_admin_can_create_userlocation_inside_room(self):
        payload = {'user_id': UserFactory().public_id, 'room_id': self.room1.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_room_admin_cannot_create_userlocation_outside_room(self):
        payload = {'user_id': UserFactory().public_id, 'room_id': self.room2.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_admin_can_update_userlocation_inside_room(self):
        payload = {'room_id': self.room1.public_id}
        response = self.client.patch(self.detail_url_in, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_room_admin_cannot_update_userlocation_outside_room(self):
        payload = {'room_id': self.room2.public_id}
        response = self.client.patch(self.detail_url_out, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_admin_can_delete_userlocation_inside_room(self):
        response = self.client.delete(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_room_admin_cannot_delete_userlocation_outside_room(self):
        response = self.client.delete(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class DepartmentViewerUserLocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.department1 = DepartmentFactory()
        self.department2 = DepartmentFactory()

        # Create locations and rooms
        self.location1 = LocationFactory(department=self.department1)
        self.location2 = LocationFactory(department=self.department2)
        self.room1 = RoomFactory(location=self.location1)
        self.room2 = RoomFactory(location=self.location2)

        # Create users
        self.department_viewer = UserFactory()
        self.user_in_dept = UserFactory()
        self.user_outside_dept = UserFactory()

        # Assign department viewer role
        RoleAssignment.objects.create(
            user=self.department_viewer,
            role="DEPARTMENT_VIEWER",
            department=self.department1
        )
        self.department_viewer.active_role = RoleAssignment.objects.get(user=self.department_viewer)
        self.department_viewer.save()

        # Create UserLocations
        self.userlocation_in_dept = UserLocationFactory(user=self.user_in_dept, room=self.room1)
        self.userlocation_outside_dept = UserLocationFactory(user=self.user_outside_dept, room=self.room2)

        # Authenticate as department viewer
        self.client.force_authenticate(user=self.department_viewer)

        # Reverse URLs
        self.list_url = reverse('userlocation-list-create')
        self.detail_url_in = reverse('userlocation-detail', args=[self.userlocation_in_dept.public_id])
        self.detail_url_out = reverse('userlocation-detail', args=[self.userlocation_outside_dept.public_id])

    # READ tests
    def test_department_viewer_can_list_userlocations_in_department(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.userlocation_in_dept.public_id, returned_ids)
        self.assertNotIn(self.userlocation_outside_dept.public_id, returned_ids)

    def test_department_viewer_can_retrieve_userlocation_inside_department(self):
        response = self.client.get(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_viewer_cannot_retrieve_userlocation_outside_department(self):
        response = self.client.get(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # WRITE tests (should all be forbidden)
    def test_department_viewer_cannot_create_userlocation(self):
        payload = {'user_id': UserFactory().public_id, 'room_id': self.room1.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_viewer_cannot_update_userlocation_inside_department(self):
        payload = {'room_id': self.room1.public_id}
        response = self.client.patch(self.detail_url_in, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_viewer_cannot_update_userlocation_outside_department(self):
        payload = {'room_id': self.room2.public_id}
        response = self.client.patch(self.detail_url_out, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_viewer_cannot_delete_userlocation_inside_department(self):
        response = self.client.delete(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_viewer_cannot_delete_userlocation_outside_department(self):
        response = self.client.delete(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LocationViewerUserLocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create departments and locations
        self.department1 = DepartmentFactory()
        self.department2 = DepartmentFactory()
        self.location1 = LocationFactory(department=self.department1)
        self.location2 = LocationFactory(department=self.department2)

        # Create rooms
        self.room1 = RoomFactory(location=self.location1)
        self.room2 = RoomFactory(location=self.location2)

        # Create users
        self.location_viewer = UserFactory()
        self.user_in_location = UserFactory()
        self.user_outside_location = UserFactory()

        # Assign location viewer role
        RoleAssignment.objects.create(
            user=self.location_viewer,
            role="LOCATION_VIEWER",
            location=self.location1
        )
        self.location_viewer.active_role = RoleAssignment.objects.get(user=self.location_viewer)
        self.location_viewer.save()

        # Create UserLocations
        self.userlocation_in_location = UserLocationFactory(user=self.user_in_location, room=self.room1)
        self.userlocation_outside_location = UserLocationFactory(user=self.user_outside_location, room=self.room2)

        # Authenticate as location viewer
        self.client.force_authenticate(user=self.location_viewer)

        # Reverse URLs
        self.list_url = reverse('userlocation-list-create')
        self.detail_url_in = reverse('userlocation-detail', args=[self.userlocation_in_location.public_id])
        self.detail_url_out = reverse('userlocation-detail', args=[self.userlocation_outside_location.public_id])

    # READ tests
    def test_location_viewer_can_list_userlocations_in_their_location(self):
        response = self.client.get(self.list_url)
        returned_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.userlocation_in_location.public_id, returned_ids)
        self.assertNotIn(self.userlocation_outside_location.public_id, returned_ids)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_location_viewer_can_retrieve_userlocation_inside_location(self):
        response = self.client.get(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_location_viewer_cannot_retrieve_userlocation_outside_location(self):
        response = self.client.get(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # WRITE tests
    def test_location_viewer_cannot_create_userlocation(self):
        payload = {'user_id': UserFactory().public_id, 'room_id': self.room1.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_viewer_cannot_update_userlocation_inside_location(self):
        payload = {'room_id': self.room1.public_id}
        response = self.client.patch(self.detail_url_in, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_viewer_cannot_delete_userlocation_inside_location(self):
        response = self.client.delete(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_viewer_cannot_create_userlocation_outside_location(self):
        payload = {'user_id': UserFactory().public_id, 'room_id': self.room2.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_viewer_cannot_update_userlocation_outside_location(self):
        payload = {'room_id': self.room2.public_id}
        response = self.client.patch(self.detail_url_out, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_location_viewer_cannot_delete_userlocation_outside_location(self):
        response = self.client.delete(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RoomViewerUserLocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create departments and locations
        self.department = DepartmentFactory()
        self.location = LocationFactory(department=self.department)

        # Create rooms
        self.room1 = RoomFactory(location=self.location)
        self.room2 = RoomFactory(location=self.location)

        # Create users
        self.room_viewer = UserFactory()
        self.user_in_room = UserFactory()
        self.user_outside_room = UserFactory()

        # Assign ROOM_VIEWER role
        RoleAssignment.objects.create(
            user=self.room_viewer,
            role="ROOM_VIEWER",
            room=self.room1
        )
        self.room_viewer.active_role = RoleAssignment.objects.get(user=self.room_viewer)
        self.room_viewer.save()

        # Create UserLocations
        self.userlocation_in_room = UserLocationFactory(user=self.user_in_room, room=self.room1)
        self.userlocation_outside_room = UserLocationFactory(user=self.user_outside_room, room=self.room2)

        # Authenticate as room viewer
        self.client.force_authenticate(user=self.room_viewer)

        # Reverse URLs
        self.list_url = reverse('userlocation-list-create')
        self.detail_url_in = reverse('userlocation-detail', args=[self.userlocation_in_room.public_id])
        self.detail_url_out = reverse('userlocation-detail', args=[self.userlocation_outside_room.public_id])

    # READ permissions
    def test_room_viewer_can_list_userlocations_in_their_room(self):
        response = self.client.get(self.list_url)
        returned_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.userlocation_in_room.public_id, returned_ids)
        self.assertNotIn(self.userlocation_outside_room.public_id, returned_ids)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_room_viewer_can_retrieve_userlocation_inside_room(self):
        response = self.client.get(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_room_viewer_cannot_retrieve_userlocation_outside_room(self):
        response = self.client.get(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # WRITE permissions blocked
    def test_room_viewer_cannot_create_userlocation(self):
        payload = {'user_id': UserFactory().public_id, 'room_id': self.room1.public_id}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_viewer_cannot_update_userlocation_inside_room(self):
        payload = {'room_id': self.room1.public_id}
        response = self.client.patch(self.detail_url_in, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_viewer_cannot_delete_userlocation_inside_room(self):
        response = self.client.delete(self.detail_url_in)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_viewer_cannot_update_userlocation_outside_room(self):
        payload = {'room_id': self.room2.public_id}
        response = self.client.patch(self.detail_url_out, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_viewer_cannot_delete_userlocation_outside_room(self):
        response = self.client.delete(self.detail_url_out)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserLocationBoundaryTests(APITestCase):
    """
    Test edge cases for UserLocation permissions, including null references
    and scope edge conditions.
    """

    def setUp(self):
        # 1. Create a Department
        self.department = DepartmentFactory(name="IT Department")
        
        # 2. Create a Location linked to the Department
        self.location = LocationFactory(department=self.department, name="Main Office")
        
        # 3. Create a Room linked to the Location
        self.normal_room = RoomFactory(location=self.location, name="Conference Room A")
        
        # 4. Create a User with a valid email
        self.user = User.objects.create_user(
            email='testuser@example.com', 
            password='password',
            fname='Test',
            lname='User'
        )

        # 5. Create a viewer user
        self.viewer = User.objects.create_user(
            email='viewer@example.com',
            password='password',
            fname='Viewer',
            lname='User'
        )

        # 6. Assign ROOM_VIEWER role for viewer
        self.viewer_role = RoleAssignment.objects.create(
            user=self.viewer,
            role="ROOM_VIEWER",
            room=self.normal_room
        )
        self.viewer.active_role = self.viewer_role
        self.viewer.save()

        # 7. Create UserLocation instances
        self.ul_normal = UserLocation.objects.create(
            user=self.user,
            room=self.normal_room,
            is_current=False
        )
        self.ul_null_room = UserLocation.objects.create(
            user=self.user,
            room=None,
            is_current=False
        )

        # 8. APIClient authentication
        self.client = APIClient()
        self.client.force_authenticate(user=self.viewer)

        # 9. Define URLs (assume DRF viewsets with pk lookup by public_id)
        self.list_url = reverse('userlocation-list-create')  # Adjust to your actual DRF view name
        self.detail_url_normal = reverse('userlocation-detail', args=[self.ul_normal.public_id])
        self.detail_url_null_room = reverse('userlocation-detail', args=[self.ul_null_room.public_id])

    # ----- Null room/location/department -----
    def test_userlocation_with_null_room_returns_403_for_viewer(self):
        response = self.client.get(self.detail_url_null_room)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_userlocation_with_null_room_cannot_be_updated(self):
        payload = {'room_id': self.ul_normal.room.public_id}
        response = self.client.patch(self.detail_url_null_room, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_userlocation_with_null_room_cannot_be_deleted(self):
        response = self.client.delete(self.detail_url_null_room)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----- Normal room within scope -----
    def test_userlocation_normal_room_can_be_listed(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [ul['public_id'] for ul in response.data]
        self.assertIn(self.ul_normal.public_id, returned_ids)
        self.assertNotIn(self.ul_null_room.public_id, returned_ids)

    def test_userlocation_normal_room_can_be_retrieved(self):
        response = self.client.get(self.detail_url_normal)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ----- Active role swapping mid-operation -----
    def test_active_role_switch_updates_scope(self):
        # Initially viewer can see ul_normal
        response_before = self.client.get(self.detail_url_normal)
        self.assertEqual(response_before.status_code, status.HTTP_200_OK)

        # Change active role to something outside the department/room
        other_department = DepartmentFactory(name="Other Dept")
        other_location = LocationFactory(department=other_department)
        other_room = RoomFactory(location=other_location)

        new_role = RoleAssignment.objects.create(
            user=self.viewer,
            role="ROOM_ADMIN",
            room=other_room
        )
        self.viewer.active_role = new_role
        self.viewer.save()

        # Now trying to access the original UserLocation should fail
        response_after = self.client.get(self.detail_url_normal)
        self.assertEqual(response_after.status_code, status.HTTP_403_FORBIDDEN)