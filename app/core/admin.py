# Django admin customization

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as translate

from core import models


class UserAdmin(BaseUserAdmin):
    # Define the admin pages for users
    ordering = ['id']
    list_display = ['email', 'name']
    # fieldsets is a 'tuple' to represent a section of the
    # admin page
    # The first value is the 'section header', which
    # we can set as None if we don't want a section header
    # Then we create a dictionary, with the key of fields
    # The value for the fields is a tuple of field names
    # which correlate to model fields
    # Best practice is that we use the 'translate'
    # so that way if other languages are added, the form
    # will display their translation for the headers rather than
    # their english-only values
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            translate('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser'
                )
            }
        ),
        (translate('Important dates'), {'fields': ('last_login',)})
    )
    readonly_fields = ['last_login']

    add_fieldsets = (
        (translate('Basic information'), {
            'classes': ('wide'),
            'fields': (
                'email',
                'password1',
                'password2',
                'name'
            )
        }),
        (translate('Permissions'), {
            'classes': ('wide'),
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser'
            ),
        })
    )


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Recipe)
