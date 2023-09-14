# Serializers for recipe APIs

from rest_framework import serializers
from core.models import Recipe


class RecipeSerializer(serializers.ModelSerializer):
    # Serializers for recipe model
    # An extension of ModelSerializer

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link']
        read_only_fields = ['id']


class RecipeDetailSerializer(RecipeSerializer):
    # Serializer for recipe detail view
    # Is an extension of the RecipeSerializer,
    # which is an extension of the ModelSerializer

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']
