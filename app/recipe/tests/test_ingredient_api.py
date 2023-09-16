from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='user@example.com', password='testpass123'):
    # Create and return a new user
    return get_user_model().objects.create_user(email=email, password=password)


def create_ingredient(user, name='Salt'):
    # Helper to create and return a tag
    return Ingredient.objects.create(user=user, name=name)


def detail_url(ingred_id):
    return reverse('recipe:ingredient-detail', args=[ingred_id])


class PublicIngredientssAPITests(TestCase):
    # Test unauthentication API requests
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        # Test auth is required for API call
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientssAPITests(TestCase):
    # Test authenticated API requests
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        # Test retrieving a list of tags
        create_ingredient(user=self.user, name="Salt")
        create_ingredient(user=self.user, name="Pepper")

        res = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_list_limited_to_user(self):
        # Test list of recipes is limited to authenticated user
        other_user = create_user(
            email='other@example.com',
            password='password123'
        )
        create_ingredient(user=other_user)
        create_ingredient(user=self.user)

        res = self.client.get(INGREDIENTS_URL)

        recipes = Ingredient.objects.filter(user=self.user)
        serializer = IngredientSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_update_ingredient(self):
        # Test updating an ingredient
        ingredient = create_ingredient(user=self.user)
        payload = {'name': 'Pepper'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)
        ingredient.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        # Test deleting tag
        ingredient = create_ingredient(self.user)
        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())
