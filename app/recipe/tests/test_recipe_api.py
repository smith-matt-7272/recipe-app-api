# Tests for recipe APIS

import os
import tempfile

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    # Create and return a recipe detail url
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    # Create and return an image upload URL
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    # Create and return a sample recipe
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://excample.com/recipe.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    # Create a new user
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    # Test public recipe API
    # public in this context is 'unauthenticated'

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        # Test auth is required for API call
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    # Test private recipe API
    # private in this context is 'authenticated'

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        # Test retrieving a list of recipes
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        # Test list of recipes is limited to authenticated user
        other_user = create_user(
            email='other@example.com',
            password='password123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        # Test getting recipe detail
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        # Test creating a recipe via API
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99')
        }
        res = self.client.post(RECIPES_URL, payload)
        # Confirm that we received a successful status
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Attempt to get the recipe from the database
        recipe = Recipe.objects.get(id=res.data['id'])
        # Loop through the payload, and validate
        # against the recipe retrieved from the DB
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        # Confirm that the recipe author is the
        # current user
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        # Test partial update of a recipe
        # such as updating a single field
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_udpate(self):
        # Test a full update of recipe
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://example.com/recipe.pdf',
            description='Sample recipe description'
        )
        # New attributes of the recipe
        payload = {
            'title': 'New title',
            'link': 'https://example.ca/recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50')
        }
        # Request the update
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        # Verify successful
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Reload the recipe from the DB
        recipe.refresh_from_db()
        # Validate that the refreshed recipe
        # matches the sent payload
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        # Test that attempt to change a recipe user
        # causes error
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=self.user)
        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        # Test deleting a recipe is successful
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        # Test trying to delete another users recipe
        # gives and error
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        # Test creating a recipe with tags
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        # Test creating a recipe with a pre-existing tag
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Delish',
            'time_minutes': 1000,
            'price': Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        # Test creating a tag when updating recipe
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Canadian'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Canadian')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        # Test assigning an exsting tag when updating a recipe
        tag_canadian = Tag.objects.create(user=self.user, name='Canadian')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_canadian)

        tag_dessert = Tag.objects.create(user=self.user, name='Dessert')
        payload = {'tags': [{'name': 'Dessert'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_dessert, recipe.tags.all())
        self.assertNotIn(tag_canadian, recipe.tags.all())

    def test_clear_recipe_tags(self):
        # Test clearing a recipes tags
        tag_canadian = Tag.objects.create(user=self.user, name='Canadian')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_canadian)
        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(tag_canadian, recipe.tags.all())

    def test_create_recipe_with_new_ingredients(self):
        # Test creating a recipe with tags
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}],
            'ingredients': [{'name': 'Salt'}, {'name': 'Pepper'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingred in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingred['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        # Test creating a recipe with tags
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}],
            'ingredients': [{'name': 'Salt'}, {'name': 'Pepper'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingred in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingred['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        # Test creating a tag when updating recipe
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{'name': 'Salt'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Salt')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        # Test assigning an exsting tag when updating a recipe
        ingredient_salt = Ingredient.objects.create(
            user=self.user,
            name='Salt'
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_salt)

        ingredient_pepper = Ingredient.objects.create(
            user=self.user,
            name='Pepper'
        )
        payload = {'ingredients': [{'name': 'Pepper'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_pepper, recipe.ingredients.all())
        self.assertNotIn(ingredient_salt, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        # Test clearing a recipes tags
        ingredient_salt = Ingredient.objects.create(
            user=self.user,
            name='Salt'
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_salt)
        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient_salt, recipe.ingredients.all())

    def test_filter_by_tags(self):
        # Test filtering recipes by tags
        r1 = create_recipe(user=self.user, title='Delicious grub')
        r2 = create_recipe(user=self.user, title='Nasty grub')
        r3 = create_recipe(user=self.user, title='Mediocre grub')
        tag1 = Tag.objects.create(user=self.user, name='Good')
        tag2 = Tag.objects.create(user=self.user, name='Bad')
        r1.tags.add(tag1)
        r2.tags.add(tag2)

        params = {'tags': f'{tag1.id}, {tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        # Test filtering recipes by ingredients
        r1 = create_recipe(user=self.user, title='Delicious grub')
        r2 = create_recipe(user=self.user, title='Nasty grub')
        r3 = create_recipe(user=self.user, title='Mediocre grub')
        ingred1 = Ingredient.objects.create(user=self.user, name='Salt')
        ingred2 = Ingredient.objects.create(user=self.user, name='Sugar')
        r1.ingredients.add(ingred1)
        r2.ingredients.add(ingred2)

        params = {'ingredients': f'{ingred1.id}, {ingred2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    # Tests for the image upload API

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        # Test uploading an image to a recipe
        url = image_upload_url(self.recipe.id)
        # Here we are creating an image file
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            # Specify the size of the file (pixel dimensions)
            img = Image.new('RGB', (10, 10))
            # Save the image to the image_file
            img.save(image_file, format='JPEG')
            # Move the pointer back to the start of the file
            image_file.seek(0)
            payload = {'image': image_file}
            # Make sure to use multipart for http content
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        # Test uploading invalid image
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'not an image'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
