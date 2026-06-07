from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_USER = 'USER'
    ROLE_ORGANIZER = 'ORGANIZER'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CONTROLLER = 'CONTROLLER'

    ROLE_CHOICES = [
        (ROLE_USER, 'Utilisateur'),
        (ROLE_ORGANIZER, 'Organisateur'),
        (ROLE_ADMIN, 'Administrateur'),
        (ROLE_CONTROLLER, 'Contrôleur'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    two_factor_enabled = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_organizer(self):
        return self.role == self.ROLE_ORGANIZER or self.is_superuser

    def is_controller(self):
        return self.role == self.ROLE_CONTROLLER or self.is_superuser

    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser
