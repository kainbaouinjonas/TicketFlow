from django.db import models
from reservations.models import Reservation

class Payment(models.Model):
    METHOD_CARD = 'CARD'
    METHOD_PAYPAL = 'PAYPAL'
    METHOD_ORANGE = 'ORANGE_MONEY'
    METHOD_MTN = 'MTN_MOMO'

    METHOD_CHOICES = [
        (METHOD_CARD, 'Carte bancaire'),
        (METHOD_PAYPAL, 'PayPal'),
        (METHOD_ORANGE, 'Orange Money'),
        (METHOD_MTN, 'MTN Mobile Money'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_SUCCESS, 'Payé'),
        (STATUS_FAILED, 'Échoué'),
    ]

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Réservation"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant")
    currency = models.CharField(max_length=10, default='EUR', verbose_name="Devise")
    method = models.CharField(max_length=30, choices=METHOD_CHOICES, default=METHOD_CARD, verbose_name="Moyen de paiement")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="Statut")
    transaction_id = models.CharField(max_length=255, unique=True, verbose_name="ID de transaction")
    phone_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Numéro de téléphone")
    otp_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Code OTP")
    gateway_logs = models.TextField(blank=True, null=True, verbose_name="Logs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']

    def __str__(self):
        return f"Paiement {self.transaction_id} - {self.amount} €"