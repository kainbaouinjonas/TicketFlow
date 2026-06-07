import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

def broadcast_seat_update(seat):
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"event_{seat.event.id}",
                {
                    'type': 'seat_update',
                    'seat_id': seat.id,
                    'status': seat.status,
                    'row': seat.row,
                    'number': seat.number,
                    'price': float(seat.price),
                    'category': seat.category,
                }
            )
    except Exception as e:
        logger.error(f"Broadcast error: {e}")

@receiver(post_save, sender='events.Seat')
def seat_post_save(sender, instance, created, **kwargs):
    if not created:
        broadcast_seat_update(instance)