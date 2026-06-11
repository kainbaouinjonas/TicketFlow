import logging
import hmac
import hashlib
import uuid
from celery import shared_task
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_tickets_async(self, reservation_id):
    """
    Génère les billets (avec signature HMAC) pour une réservation confirmée.
    Tâche asynchrone pour ne pas bloquer le flux de paiement.
    """
    try:
        from reservations.models import Reservation
        from tickets.models import Ticket

        reservation = Reservation.objects.prefetch_related('seats').get(id=reservation_id)

        if reservation.status != Reservation.STATUS_CONFIRMED:
            logger.warning(f"Réservation {reservation_id} pas confirmée, skip.")
            return f"Réservation {reservation_id} non confirmée"

        # Vérifier si les billets existent déjà
        if reservation.tickets.exists():
            logger.info(f"Billets déjà générés pour la réservation {reservation_id}")
            return f"Billets déjà existants pour la réservation {reservation_id}"

        from payments.views import generate_tickets_for_reservation
        generate_tickets_for_reservation(reservation)

        created_count = reservation.tickets.count()
        logger.info(f"{created_count} billets générés pour la réservation {reservation_id}")
        return f"{created_count} billets créés pour la réservation {reservation_id}"

    except Exception as exc:
        logger.error(f"Erreur génération billets réservation {reservation_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_orphaned_tickets():
    """
    Supprime les billets associés à des réservations annulées.
    À exécuter périodiquement via Celery Beat.
    """
    from reservations.models import Reservation
    from tickets.models import Ticket

    orphaned = Ticket.objects.filter(
        reservation__status=Reservation.STATUS_CANCELLED
    )
    count = orphaned.count()
    orphaned.delete()

    logger.info(f"Nettoyage : {count} billets orphelins supprimés")
    return f"{count} billets orphelins supprimés"
