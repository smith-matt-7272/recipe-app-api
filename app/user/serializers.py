# Serializers for the user API View

from django.contrib.auth import (
    get_user_model,
    authenticate
)
from django.utils.translation import gettext
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    # Serializer for the user object

    # We set the 'meta' of the serializer so that is knows
    # which model we are using, the fields which will be
    # included, plus some options such as validation rules
    # and read/write rules
    class Meta:
        model = get_user_model()
        # We don't want users to be able to set things like
        # is_staff or is_superuser, hence we exclude them
        fields = ['email', 'password', 'name']
        # If the request against the serializer violates these rules
        # then it returns a bad request
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5}}

    # This gets called AFTER the validation is performed and is
    # successful
    def create(self, validated_data):
        # Create and return a user with encrypted password
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        # Update and return user

        # Remove the password from the validated data
        # Default to a None, as it isn't required for
        # the update
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class AuthTokenSerializer(serializers.Serializer):
    # Serializer for the user auth token
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )

        if not user:
            msg = gettext('Unable to authenticate with provided credentials')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs
