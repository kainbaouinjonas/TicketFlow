import json
import logging
from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer
from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class SeatMapConsumer(JsonWebsocketConsumer):
    """
    Consumer WebSocket pour les mises à jour en temps réel du plan de salle.
    Utilise JsonWebsocketConsumer pour une gestion simplifiée des messages JSON.
    """
    
    def connect(self):
        """Gère la connexion WebSocket"""
        try:
            # Récupérer l'ID de l'événement depuis l'URL
            self.event_id = self.scope['url_route']['kwargs'].get('event_id')
            self.event_slug = self.scope['url_route']['kwargs'].get('event_slug')
            
            # Utiliser l'ID ou le slug
            identifier = self.event_id or self.event_slug
            if not identifier:
                logger.warning("Connexion WebSocket sans identifiant d'événement")
                self.close()
                return
            
            self.room_group_name = f"event_{identifier}"
            
            # Vérifier si l'événement existe (optionnel)
            if not self.event_exists(identifier):
                logger.warning(f"Tentative de connexion à un événement inexistant: {identifier}")
                self.close()
                return
            
            # Rejoindre le groupe de room
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )
            
            # Accepter la connexion
            self.accept()
            
            # Log de connexion (si utilisateur authentifié)
            user = self.scope.get('user')
            if user and user.is_authenticated:
                logger.info(f"WebSocket connecté: Utilisateur {user.username} - Événement {identifier}")
            
            # Envoyer un message de bienvenue
            self.send_json({
                'type': 'connected',
                'message': f'Connecté à l\'événement {identifier}',
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la connexion WebSocket: {str(e)}")
            self.close()
    
    def disconnect(self, close_code):
        """Gère la déconnexion WebSocket"""
        try:
            # Quitter le groupe de room
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name,
                self.channel_name
            )
            
            # Log de déconnexion
            user = self.scope.get('user')
            if user and user.is_authenticated:
                logger.info(f"WebSocket déconnecté: Utilisateur {user.username} - Code {close_code}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion WebSocket: {str(e)}")
    
    def receive_json(self, content):
        """
        Reçoit un message JSON du client WebSocket.
        """
        try:
            message_type = content.get('type')
            
            # Heartbeat (ping/pong)
            if message_type == 'ping':
                self.send_json({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                })
            
            # Demande de rafraîchissement des sièges
            elif message_type == 'refresh_seats':
                # Le client demande une mise à jour complète
                self.send_json({
                    'type': 'refresh',
                    'message': 'Demande de rafraîchissement reçue'
                })
                # Optionnel: déclencher un broadcast de tous les sièges
                self.broadcast_all_seats()
            
            # Message non reconnu
            else:
                logger.debug(f"Message WebSocket non reconnu: {message_type}")
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message WebSocket: {str(e)}")
            self.send_json({
                'type': 'error',
                'message': 'Erreur lors du traitement de votre message'
            })
    
    def seat_update(self, event):
        """
        Reçoit une mise à jour de siège depuis le groupe de room.
        Envoie au client WebSocket.
        """
        try:
            self.send_json({
                'type': 'seat_update',
                'seat_id': event.get('seat_id'),
                'status': event.get('status'),
                'row': event.get('row'),
                'number': event.get('number'),
                'price': float(event.get('price', 0)),
                'category': event.get('category'),
                'version': event.get('version', 1),
                'timestamp': timezone.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la mise à jour de siège: {str(e)}")
    
    def bulk_seat_update(self, event):
        """
        Reçoit une mise à jour groupée de plusieurs sièges.
        """
        try:
            self.send_json({
                'type': 'bulk_seat_update',
                'seats': event.get('seats', []),
                'timestamp': timezone.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la mise à jour groupée: {str(e)}")
    
    def event_status(self, event):
        """
        Reçoit une mise à jour du statut global de l'événement.
        """
        try:
            self.send_json({
                'type': 'event_status',
                'status': event.get('status'),
                'available_seats': event.get('available_seats'),
                'reserved_seats': event.get('reserved_seats'),
                'locked_seats': event.get('locked_seats'),
                'timestamp': timezone.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du statut d'événement: {str(e)}")
    
    @database_sync_to_async
    def event_exists(self, identifier):
        """Vérifie si l'événement existe dans la base de données"""
        from events.models import Event
        try:
            if identifier.isdigit():
                return Event.objects.filter(id=int(identifier)).exists()
            else:
                return Event.objects.filter(slug=identifier).exists()
        except Exception:
            return False
    
    def broadcast_all_seats(self):
        """Diffuse tous les sièges de l'événement (optionnel)"""
        from events.models import Seat
        from django.core.serializers import serialize
        import json
        
        try:
            if self.event_id:
                seats = Seat.objects.filter(event_id=self.event_id).values(
                    'id', 'row', 'number', 'status', 'price', 'category', 'version'
                )
                seat_list = list(seats)
                
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'bulk_seat_update',
                        'seats': seat_list
                    }
                )
        except Exception as e:
            logger.error(f"Erreur lors du broadcast des sièges: {str(e)}")


class AsyncSeatMapConsumer(AsyncJsonWebsocketConsumer):
    """
    Version asynchrone du consumer pour de meilleures performances.
    À utiliser avec des bases de données asynchrones.
    """
    
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs'].get('event_id')
        self.event_slug = self.scope['url_route']['kwargs'].get('event_slug')
        identifier = self.event_id or self.event_slug
        
        if not identifier:
            await self.close()
            return
        
        self.room_group_name = f"event_{identifier}"
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send_json({
            'type': 'connected',
            'message': f'Connecté à l\'événement {identifier}',
            'timestamp': timezone.now().isoformat()
        })
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        message_type = content.get('type')
        
        if message_type == 'ping':
            await self.send_json({
                'type': 'pong',
                'timestamp': timezone.now().isoformat()
            })
    
    async def seat_update(self, event):
        await self.send_json({
            'type': 'seat_update',
            'seat_id': event['seat_id'],
            'status': event['status'],
            'row': event['row'],
            'number': event['number'],
            'price': float(event['price']),
            'category': event['category'],
            'timestamp': timezone.now().isoformat()
        })