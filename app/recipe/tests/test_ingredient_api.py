
from core.models import Ingredient, Recipe
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


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

    def test_filter_ingredients_assigned_to_recipes(self):
        # Test listing ingredients by those assigned to recipes
        i1 = Ingredient.objects.create(user=self.user, name='Salt')
        i2 = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = Recipe.objects.create(
            title="Sammich",
            time_minutes=5,
            price=Decimal('1.00'),
            user=self.user
        )
        recipe.ingredients.add(i1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(i1)
        s2 = IngredientSerializer(i2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        # Test filtered ingredients returns a unique list
        i1 = Ingredient.objects.create(user=self.user, name='Salt')
        Ingredient.objects.create(user=self.user, name='Pepper')
        r1 = Recipe.objects.create(
            title="Sammich",
            time_minutes=5,
            price=Decimal('1.00'),
            user=self.user
        )
        r2 = Recipe.objects.create(
            title="Ham Sammich",
            time_minutes=5,
            price=Decimal('1.00'),
            user=self.user
        )
        r1.ingredients.add(i1)
        r2.ingredients.add(i1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
