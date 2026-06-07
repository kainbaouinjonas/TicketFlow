from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin view for the custom User model."""

    # Columns displayed in the list view
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'is_active', 'is_staff', 'date_joined',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)

    # Add custom fields to the fieldsets shown in the detail view
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Informations supplémentaires'), {
            'fields': ('role', 'phone_number', 'two_factor_enabled', 'avatar'),
        }),
    )

    # Fields shown when creating a new user from admin
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Informations supplémentaires'), {
            'fields': ('email', 'role', 'phone_number'),
        }),
    )

    # Allow quick editing of is_active directly from the list
    list_editable = ('is_active',)

    actions = ['activate_users', 'deactivate_users', 'set_role_organizer', 'set_role_user']

    @admin.action(description='✅ Activer les comptes sélectionnés')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} compte(s) activé(s) avec succès.')

    @admin.action(description='🚫 Désactiver les comptes sélectionnés')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} compte(s) désactivé(s).')

    @admin.action(description='🎭 Définir le rôle: Organisateur')
    def set_role_organizer(self, request, queryset):
        updated = queryset.update(role=User.ROLE_ORGANIZER)
        self.message_user(request, f'{updated} utilisateur(s) défini(s) comme Organisateur.')

    @admin.action(description='👤 Définir le rôle: Utilisateur')
    def set_role_user(self, request, queryset):
        updated = queryset.update(role=User.ROLE_USER)
        self.message_user(request, f'{updated} utilisateur(s) défini(s) comme Utilisateur.')
