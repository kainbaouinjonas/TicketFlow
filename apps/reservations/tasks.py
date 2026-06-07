from celery import shared_task
from django.utils import timezone
from django.db import transaction
from events.models import Seat
from .models import Cart, Reservation
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_seat_update(seat):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"event_{seat.event.id}",
            {
                "type": "seat_update",
                "seat_id": seat.id,
                "status": seat.status,
                "row": seat.row,
                "number": seat.number,
                "price": float(seat.price),
                "category": seat.category,
            }
        )

@shared_task
def release_expired_carts_and_reservations():
    now = timezone.now()
    
    expired_carts = Cart.objects.filter(expires_at__lt=now)
    cart_count = expired_carts.count()
    
    for cart in expired_carts:
        try:
            with transaction.atomic():
                items = cart.items.all().select_related('seat')
                for item in items:
                    seat = item.seat
                    seat.status = Seat.STATUS_AVAILABLE
                    seat.locked_by_session = None
                    seat.locked_at = None
                    seat.save()
                    broadcast_seat_update(seat)
                items.delete()
                cart.delete()
        except Exception as e:
            print(f"Error releasing cart {cart.id}: {e}")

    expired_reservations = Reservation.objects.filter(status=Reservation.STATUS_PENDING, expires_at__lt=now)
    res_count = expired_reservations.count()
    
    for res in expired_reservations:
        try:
            with transaction.atomic():
                res.status = Reservation.STATUS_CANCELLED
                res.save()
                for seat in res.seats.all():
                    seat.status = Seat.STATUS_AVAILABLE
                    seat.locked_by_session = None
                    seat.locked_at = None
                    seat.save()
                    broadcast_seat_update(seat)
        except Exception as e:
            print(f"Error releasing reservation {res.id}: {e}")
            
    return f"Released {cart_count} expired carts and {res_count} expired reservations."