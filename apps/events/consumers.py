import json
import logging
from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync

logger = logging.getLogger('websocket')

class SeatMapConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.event_id = self.scope['url_route']['kwargs'].get('event_id')
        if not self.event_id:
            self.close()
            return
            
        self.room_group_name = f"event_{self.event_id}"

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
        logger.info(f"WebSocket connected for event {self.event_id}")

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected for event {self.event_id}")

    def receive_json(self, content):
        message_type = content.get('type')
        if message_type == 'ping':
            self.send_json({'type': 'pong'})

    def seat_update(self, event):
        self.send_json({
            'type': 'seat_update',
            'seat_id': event['seat_id'],
            'status': event['status'],
            'row': event['row'],
            'number': event['number'],
            'price': float(event['price']),
            'category': event['category'],
        })