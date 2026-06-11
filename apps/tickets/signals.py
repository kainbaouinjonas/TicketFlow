from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from reservations.models import Reservation
from tickets.tasks import generate_tickets_async


@receiver(post_save, sender=Reservation)
def create_tickets_on_reservation_confirmed(sender, instance, **kwargs):
    if instance.status == Reservation.STATUS_CONFIRMED:
        transaction.on_commit(lambda: generate_tickets_async.delay(instance.id))