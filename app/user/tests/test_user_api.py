# Tests for the User API

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    # Create and return a new user
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    # Test the public features of the User API
    # Public in this context means unauthenticated

    # setUp is a method performed before each test
    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        # Test creating a user is successful
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name'
        }
        # Perform a post request against the User API
        # sending the above payload
        res = self.client.post(CREATE_USER_URL, payload)
        # Ensure that we have a successful request
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Get the new user from the DB via their email
        user = get_user_model().objects.get(email=payload['email'])
        # Check that the plaintext password matches the user
        # retrieved from the DB
        self.assertTrue(user.check_password(payload['password']))
        # Validate that the plaintext password is NOT in the
        # response body
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        # Test error returned if user with email exists
        # Duplicate the payload from test_create_user_success
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name'
        }
        # Add the user to the db directly
        create_user(**payload)
        # Perform a post request against the User API
        # sending the above payload
        res = self.client.post(CREATE_USER_URL, payload)
        # Should get a bad request response back; user already exists
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        # Test an error is returned if password is less than 5 chars
        # Payload PW is too short
        payload = {
            'email': 'test@example.com',
            'password': 'pass',
            'name': 'Test Name'
        }
        # Perform a post request against the User API
        # sending the above payload
        res = self.client.post(CREATE_USER_URL, payload)
        # Should get a bad request response back; user already exists
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Query for the user by email
        # Exists is a method which flags if a result comes back or not
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        # User should not exist
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        # Test generating token for valid credentials

        # Create a user
        user_details = {
            'email': 'test@example.com',
            'password': 'test-user-pass123',
            'name': 'Test Name'
        }
        create_user(**user_details)
        # Perform token request with that user info
        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }
        res = self.client.post(TOKEN_URL, payload)
        # Validate that token is in the response body, and
        # that request was successful
        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        # Test returns error if credentials invalid

        # Create a user
        user_details = {
            'email': 'test@example.com',
            'password': 'test-user-pass123',
            'name': 'Test Name'
        }
        create_user(**user_details)
        # Perform token request with that user info but
        # incorrect password
        payload = {
            'email': user_details['email'],
            'password': 'badpassword'
        }
        res = self.client.post(TOKEN_URL, payload)
        # Validate that token is NOT in the response body, and
        # that request was bad
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        # Test posting a blank password returns error

        # Create a user
        user_details = {
            'email': 'test@example.com',
            'password': 'test-user-pass123',
            'name': 'Test Name'
        }
        create_user(**user_details)
        # Perform token request with that user info but
        # incorrect password
        payload = {
            'email': user_details['email'],
            'password': ''
        }
        res = self.client.post(TOKEN_URL, payload)
        # Validate that token is NOT in the response body, and
        # that request was bad
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        # Test authentication is required for users
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    # Test the private features of the User API
    # Private in this context is authenticated

    def setUp(self):
        # Create our test user
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='Test Name'
        )
        self.client = APIClient()
        # Pretend the user is authenticated
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        # Test that retrieving profile for logged in user
        # is successful
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email
        })

    def test_post_me_not_allowed(self):
        # Test that POST is not allowed for the ME endpoint
        res = self.client.post(ME_URL, {})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        # Test updating the user profile for the authenticated user
        payload = {
            'password': 'NewPassword123',
            'name': 'Updated Name'
        }
        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
