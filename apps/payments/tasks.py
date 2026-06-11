import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_payment_confirmation_email(self, payment_id):
    """
    Envoie un email de confirmation après un paiement réussi.
    Tâche asynchrone pour ne pas bloquer la réponse HTTP.
    """
    try:
        from payments.models import Payment

        payment = Payment.objects.select_related(
            'reservation', 'reservation__user'
        ).get(id=payment_id)

        user = payment.reservation.user
        if not user or not user.email:
            logger.warning(f"Payment {payment_id}: pas d'email utilisateur")
            return f"Pas d'email pour le paiement {payment_id}"

        subject = f"TicketFlow — Confirmation de paiement #{payment.transaction_id}"
        message = (
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            f"Votre paiement de {payment.amount} {payment.currency} a été confirmé.\n"
            f"Méthode : {payment.get_method_display()}\n"
            f"Transaction : {payment.transaction_id}\n\n"
            f"Vos billets sont disponibles dans votre espace personnel.\n\n"
            f"Merci d'avoir choisi TicketFlow !\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Email de confirmation envoyé pour le paiement {payment_id}")
        return f"Email envoyé à {user.email} pour le paiement {payment_id}"

    except Exception as exc:
        logger.error(f"Erreur envoi email paiement {payment_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_failed_payments():
    """
    Nettoie les paiements en attente (PENDING) qui ont expiré.
    À exécuter périodiquement via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from payments.models import Payment

    threshold = timezone.now() - timedelta(hours=1)
    stale_payments = Payment.objects.filter(
        status=Payment.STATUS_PENDING,
        created_at__lt=threshold
    )

    count = stale_payments.update(status=Payment.STATUS_FAILED)
    logger.info(f"Nettoyage : {count} paiements expirés marqués comme échoués")
    return f"{count} paiements nettoyés"
