import uuid
import hmac
import hashlib
from django.db import models
from django.conf import settings
from reservations.models import Reservation
from events.models import Seat


class Ticket(models.Model):
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name="Réservation"
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name="Siège"
    )
    ticket_code = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="Code unique"
    )
    qr_code_hash = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Signature cryptographique"
    )
    is_validated = models.BooleanField(default=False, verbose_name="Validé")
    validated_at = models.DateTimeField(blank=True, null=True, verbose_name="Date de validation")
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='validated_tickets',
        verbose_name="Validé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Billet"
        verbose_name_plural = "Billets"
        unique_together = ('reservation', 'seat')

    def __str__(self):
        return f"Ticket {self.ticket_code} - {self.seat.event.title}"
    
    def get_qr_url(self):
        from django.urls import reverse
        return reverse('ticket_qr', kwargs={'ticket_code': self.ticket_code})