from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from ..factories import AdminUserFactory
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

User = get_user_model()

class UserLoginTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUserFactory()

    def test_create_admin_user(self):
        self.assertTrue(self.admin_user.check_password('admin'))
        self.assertTrue(self.admin_user.pk)


    def test_login_as_admin_user(self):
        response = self.client.post("/login/", {
        "email": self.admin_user.email,
        "password": "admin",
            })
        self.assertTrue(response.status_code,200 )
        self.assertTrue(self.admin_user.is_authenticated)


class JWTLoginResponseTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = AdminUserFactory()

    def test_login_data_response(self):
        url = reverse('custom_login') 
        data = {'email': self.admin_user.email, 'password': 'admin'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # test response data
        self.assertIn('access', response.data)
        self.assertIn('public_id', response.data)
        self.assertIn('fname', response.data)
        self.assertIn('lname', response.data)
        self.assertIn('active_role_id', response.data)
        self.assertIn('roles', response.data)
        # check that refresh token isn't sent
        self.assertNotIn('refresh', response.data)

    def test_refresh_token_is_httponly(self):
        url = reverse('custom_login')
        data = {'email': self.admin_user.email, 'password': 'admin'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Check that refresh token is set as a cookie
        self.assertIn('refresh', response.cookies)

        # 3. Verify HttpOnly flag
        refresh_cookie = response.cookies['refresh']
        self.assertTrue(refresh_cookie['httponly'], "Refresh token cookie is not HttpOnly")
