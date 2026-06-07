from django.db import models
from django.conf import settings
from events.models import Seat
from django.utils import timezone
from datetime import timedelta

class Cart(models.Model):
    session_id = models.CharField(max_length=255, unique=True, verbose_name="ID de session")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name="Utilisateur"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Date d'expiration")

    class Meta:
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Panier {self.session_id} (Expire à {self.expires_at})"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Panier"
    )
    seat = models.OneToOneField(
        Seat,
        on_delete=models.CASCADE,
        related_name='cart_item',
        verbose_name="Siège"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Article du panier"
        verbose_name_plural = "Articles du panier"

    def __str__(self):
        return f"Siège {self.seat} dans panier {self.cart.session_id}"


class Reservation(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente de paiement'),
        (STATUS_CONFIRMED, 'Confirmée'),
        (STATUS_CANCELLED, 'Annulée'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name="Utilisateur"
    )
    session_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="ID de session")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Statut"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix total"
    )
    seats = models.ManyToManyField(
        Seat,
        related_name='reservations',
        verbose_name="Sièges"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Expiration de réservation")

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_expired(self):
        return self.status == self.STATUS_PENDING and timezone.now() > self.expires_at

    def __str__(self):
        return f"Réservation #{self.id} - {self.status} ({self.total_price} €)"