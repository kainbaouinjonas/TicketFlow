from django.db.models.signals import post_save
from django.dispatch import receiver
from reservations.models import Reservation


@receiver(post_save, sender=Reservation)
def create_tickets_on_reservation_confirmed(sender, instance, **kwargs):
    if instance.status == Reservation.STATUS_CONFIRMED:
        from payments.views import generate_tickets_for_reservation
        generate_tickets_for_reservation(instance)