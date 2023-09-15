# Tests for the Tags api

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Tag

from recipe.serializers import (
    TagSerializer
)

TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    # Create and return a tag detail url
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='testpass123'):
    # Create and return a new user
    return get_user_model().objects.create_user(email=email, password=password)


def create_tag(user, name='Indian'):
    # Helper to create and return a tag
    return Tag.objects.create(user=user, name=name)


class PublicTagsAPITests(TestCase):
    # Test unauthentication API requests
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        # Test auth is required for API call
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITests(TestCase):
    # Test authenticated API requests
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        # Test retrieving a list of tags
        create_tag(user=self.user, name="Candy")
        create_tag(user=self.user, name="Indian")

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by('-id')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_list_limited_to_user(self):
        # Test list of recipes is limited to authenticated user
        other_user = create_user(
            email='other@example.com',
            password='password123'
        )
        create_tag(user=other_user)
        create_tag(user=self.user)

        res = self.client.get(TAGS_URL)

        recipes = Tag.objects.filter(user=self.user)
        serializer = TagSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_update_tag(self):
        # Test updating a tag
        tag = create_tag(self.user, 'Banana-based')
        payload = {'name': 'Dessert'}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)
        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        # Test deleting tag
        tag = create_tag(self.user)
        url = detail_url(tag.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())
