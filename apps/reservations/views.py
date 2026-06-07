"""
Vues des réservations avec sécurité renforcée
Protection : Race conditions, double réservation, CSRF, injection
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction, DatabaseError
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from datetime import timedelta
from events.models import Seat
from .models import Cart, CartItem, Reservation
from common.security import InputSanitizer, RateLimiter
from administration.models import AuditLog

logger = logging.getLogger('security')


def get_or_create_session_cart(request):
    """
    Récupère ou crée un panier pour la session
    Avec validation de sécurité
    """
    if not request.session.session_key:
        request.session.create()
    
    session_id = request.session.session_key
    
    # Nettoyer l'ID de session
    session_id = InputSanitizer.sanitize_text(session_id, 255)
    
    try:
        cart, created = Cart.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'expires_at': timezone.now() + timedelta(minutes=15)
            }
        )
    except DatabaseError as e:
        logger.error(f"Database error in cart creation: {str(e)}")
        return None
    
    # Si le panier est expiré, le nettoyer
    if cart.is_expired():
        with transaction.atomic():
            for item in cart.items.all():
                seat = item.seat
                seat.status = Seat.STATUS_AVAILABLE
                seat.locked_by_session = None
                seat.locked_at = None
                seat.version += 1
                seat.save()
                
                # Broadcast via WebSocket
                from websocket.signals import broadcast_seat_update
                broadcast_seat_update(seat)
            
            cart.items.all().delete()
            cart.expires_at = timezone.now() + timedelta(minutes=15)
            cart.save()
    
    return cart


@require_http_methods(["POST"])
@csrf_protect
def add_to_cart(request, seat_id):
    """
    Ajoute un siège au panier
    Protection : Race condition, double ajout, session hijacking
    """
    # Rate limiting
    limiter = RateLimiter('add_to_cart', 30, 60)
    allowed, wait = limiter.check(request.META.get('REMOTE_ADDR', 'unknown'))
    if not allowed:
        return JsonResponse({
            'success': False,
            'message': f"Trop de requêtes. Attendez {wait} secondes."
        }, status=429)
    
    # Vérifier la session
    if not request.session.session_key:
        return JsonResponse({'success': False, 'message': "Session invalide"}, status=400)
    
    cart = get_or_create_session_cart(request)
    if not cart:
        return JsonResponse({'success': False, 'message': "Erreur panier"}, status=500)
    
    session_id = request.session.session_key
    
    try:
        with transaction.atomic():
            # SELECT FOR UPDATE avec NOWAIT pour éviter les deadlocks
            try:
                seat = Seat.objects.select_for_update(nowait=True).get(id=seat_id)
            except DatabaseError:
                return JsonResponse({
                    'success': False,
                    'message': "Le système est saturé. Veuillez réessayer."
                }, status=409)
            
            # Vérifier la disponibilité
            if seat.status != Seat.STATUS_AVAILABLE:
                return JsonResponse({
                    'success': False,
                    'message': "Ce siège n'est plus disponible."
                }, status=400)
            
            # Vérifier que l'événement n'est pas passé
            if seat.event.end_time and seat.event.end_time < timezone.now():
                return JsonResponse({
                    'success': False,
                    'message': "Cet événement est déjà terminé."
                }, status=400)
            
            # Version checking (optimistic lock)
            current_version = seat.version
            
            # Verrouiller le siège
            seat.status = Seat.STATUS_LOCKED
            seat.locked_by_session = session_id
            seat.locked_at = timezone.now()
            seat.version += 1
            seat.save()
            
            # Vérifier que personne n'a modifié le siège entre temps
            if seat.version != current_version + 1:
                raise DatabaseError("Version conflict")
            
            # Ajouter au panier
            CartItem.objects.create(cart=cart, seat=seat)
            
            # Log de sécurité
            if request.user.is_authenticated:
                AuditLog.objects.create(
                    user=request.user,
                    action="Ajout au panier",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Siège {seat.row}{seat.number} - Événement {seat.event.id}"
                )
            
            # Broadcast WebSocket
            from websocket.signals import broadcast_seat_update
            broadcast_seat_update(seat)
            
            return JsonResponse({
                'success': True,
                'message': "Siège ajouté au panier",
                'cart_count': cart.items.count(),
                'seat_version': seat.version
            })
            
    except Seat.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Siège introuvable"}, status=404)
    except DatabaseError as e:
        logger.error(f"Database error in add_to_cart: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': "Erreur système. Veuillez réessayer."
        }, status=500)


@require_http_methods(["POST"])
@csrf_protect
def remove_from_cart(request, seat_id):
    """
    Retire un siège du panier
    """
    session_id = request.session.session_key
    if not session_id:
        return JsonResponse({'success': False, 'message': "Session invalide"}, status=400)
    
    try:
        with transaction.atomic():
            cart = Cart.objects.get(session_id=session_id)
            item = CartItem.objects.select_for_update().get(cart=cart, seat_id=seat_id)
            seat = item.seat
            
            # Vérifier que le siège est bien verrouillé par cette session
            if seat.locked_by_session != session_id:
                logger.warning(f"Session {session_id} tried to unlock seat {seat_id} locked by {seat.locked_by_session}")
                return JsonResponse({'success': False, 'message': "Action non autorisée"}, status=403)
            
            # Libérer le siège
            seat.status = Seat.STATUS_AVAILABLE
            seat.locked_by_session = None
            seat.locked_at = None
            seat.version += 1
            seat.save()
            
            item.delete()
            
            # Broadcast WebSocket
            from websocket.signals import broadcast_seat_update
            broadcast_seat_update(seat)
            
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': "Siège retiré du panier",
                    'cart_count': cart.items.count()
                })
            else:
                messages.success(request, "Siège retiré du panier.")
                return redirect('cart_detail')
            
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        if is_ajax:
            return JsonResponse({'success': False, 'message': "Article introuvable"}, status=404)
        else:
            messages.error(request, "Article introuvable dans votre panier.")
            return redirect('cart_detail')


@require_http_methods(["GET"])
def cart_detail(request):
    """
    Affiche le contenu du panier
    """
    cart = get_or_create_session_cart(request)
    if not cart:
        return render(request, 'reservations/cart.html', {'items': [], 'total': 0, 'time_left': 0})
    
    items = cart.items.all().select_related('seat', 'seat__event')
    total = sum(item.seat.price for item in items)
    time_left = max(0, int((cart.expires_at - timezone.now()).total_seconds())) if cart.expires_at else 0
    
    return render(request, 'reservations/cart.html', {
        'items': items,
        'total': total,
        'time_left': time_left,
        'cart_id': cart.id
    })


@require_http_methods(["GET"])
def cart_count(request):
    """
    Retourne le nombre d'articles dans le panier (AJAX)
    """
    if request.user.is_authenticated or request.session.session_key:
        cart = get_or_create_session_cart(request)
        count = cart.items.count() if cart else 0
    else:
        count = 0
    
    return JsonResponse({'count': count})


@require_http_methods(["POST"])
@csrf_protect
def create_reservation(request):
    """
    Transforme le panier en réservation
    Protection : Validation des prix, vérification des stocks
    """
    session_id = request.session.session_key
    if not session_id:
        return redirect('home')
    
    # Rate limiting
    limiter = RateLimiter('create_reservation', 10, 60)
    allowed, wait = limiter.check(request.META.get('REMOTE_ADDR', 'unknown'))
    if not allowed:
        messages.error(request, f"Trop de tentatives. Attendez {wait} secondes.")
        return redirect('cart_detail')
    
    try:
        with transaction.atomic():
            cart = Cart.objects.select_for_update().get(session_id=session_id)
            items = cart.items.all().select_related('seat', 'seat__event')
            
            if not items.exists():
                return redirect('home')
            
            # Vérifier que tous les sièges sont toujours verrouillés par cette session
            for item in items:
                if item.seat.locked_by_session != session_id:
                    logger.warning(f"Seat {item.seat.id} not locked by session {session_id}")
                    return redirect('cart_detail')
            
            # Recalculer le prix total (protection contre la modification du prix en frontend)
            total_price = sum(item.seat.price for item in items)
            
            # Vérifier que l'événement n'est pas passé
            event = items.first().seat.event
            if event.end_time and event.end_time < timezone.now():
                messages.error(request, "Cet événement est déjà terminé.")
                return redirect('cart_detail')
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                status=Reservation.STATUS_PENDING,
                total_price=total_price,
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Ajouter les sièges à la réservation
            for item in items:
                seat = item.seat
                # S'assurer que le siège est encore valide
                if seat.status != Seat.STATUS_LOCKED:
                    raise DatabaseError(f"Seat {seat.id} invalid state")
                
                reservation.seats.add(seat)
            
            # Nettoyer le panier
            items.delete()
            cart.delete()
            
            # Log
            if request.user.is_authenticated:
                AuditLog.objects.create(
                    user=request.user,
                    action="Création réservation",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Réservation #{reservation.id} - {total_price}€ - {reservation.seats.count()} sièges"
                )
            
            return redirect('checkout', reservation_id=reservation.id)
            
    except Cart.DoesNotExist:
        return redirect('home')
    except DatabaseError as e:
        logger.error(f"Database error in create_reservation: {str(e)}")
        messages.error(request, "Erreur lors de la création de la réservation. Veuillez réessayer.")
        return redirect('cart_detail')