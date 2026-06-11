from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from payments.models import Payment
from payments.tasks import send_payment_confirmation_email


@receiver(post_save, sender=Payment)
def send_email_on_payment_success(sender, instance, **kwargs):
    """
    Déclenche l'envoi asynchrone de l'email de confirmation
    lorsqu'un paiement passe au statut SUCCESS.
    """
    if instance.status == Payment.STATUS_SUCCESS:
        transaction.on_commit(lambda: send_payment_confirmation_email.delay(instance.id))

