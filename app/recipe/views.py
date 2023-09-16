# Views for the recipe API

from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Recipe, Tag, Ingredient
from recipe import serializers


class RecipeViewSet(viewsets.ModelViewSet):
    # View to manage recipe APIs

    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Retrieve recipes for authenticated user
        # This is an override of the default get queryset
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        # Return the serializer class for request
        # Note that we are returning the CLASS and
        # not an instantiated serializer
        if self.action == 'list':
            return serializers.RecipeSerializer
        # Most requests will be towards the RecipeDetailSerializer,
        # so it is set as the default for our View's serializer class
        return self.serializer_class

    def perform_create(self, serializer):
        # Create a new recipe
        serializer.save(user=self.request.user)


class TagViewSet(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):

    # View to manage Tag APIs
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return queryset for authenticated user
        return self.queryset.filter(user=self.request.user).order_by('-name')


class IngredientViewSet(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):

    # View to manage Tag APIs
    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return queryset for authenticated user
        return self.queryset.filter(user=self.request.user).order_by('-name')
