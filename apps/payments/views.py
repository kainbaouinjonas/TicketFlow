import uuid
import hmac
import hashlib
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from reservations.models import Reservation
from events.models import Seat
from .models import Payment
from .gateways import StripeMockGateway, PayPalMockGateway, MobileMoneyMockGateway
from tickets.models import Ticket
from administration.models import AuditLog

logger = logging.getLogger('security')


@login_required
@require_http_methods(["GET"])
def checkout(request, reservation_id):
    """Page de paiement - vérification de propriété"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Si la réservation a été faite anonymement mais que la session correspond, on l'associe à l'utilisateur maintenant connecté
    if reservation.user is None and reservation.session_id == request.session.session_key:
        reservation.user = request.user
        reservation.save()
        
    # Vérification critique : l'utilisateur doit être propriétaire
    if reservation.user != request.user and not request.user.is_admin():
        logger.warning(f"Unauthorized checkout access attempt: User {request.user.username} tried to access reservation {reservation_id}")
        return redirect('dashboard')
    
    if reservation.status != Reservation.STATUS_PENDING:
        messages.error(request, "Cette réservation n'est plus valide.")
        return redirect('dashboard')
    
    # Vérification d'expiration
    if reservation.is_expired():
        messages.error(request, "La réservation a expiré.")
        return redirect('cart_detail')
    
    time_left = max(0, int((reservation.expires_at - timezone.now()).total_seconds()))
    
    return render(request, 'payments/checkout.html', {
        'reservation': reservation,
        'time_left': time_left,
    })


@login_required
@require_http_methods(["POST"])
@csrf_protect
def process_payment(request):
    """
    Traitement du paiement - AVEC VALIDATION COMPLÈTE
    """
    reservation_id = request.POST.get('reservation_id')
    payment_method = request.POST.get('payment_method')
    phone_number = request.POST.get('phone_number', '').strip()
    
    # Validation des entrées
    if not reservation_id or not payment_method:
        return JsonResponse({'success': False, 'message': "Paramètres manquants"}, status=400)
    
    # Récupération et vérification de propriété
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user != request.user:
        logger.error(f"Payment fraud attempt: User {request.user.username} tried to pay for reservation {reservation_id} belonging to {reservation.user}")
        return JsonResponse({'success': False, 'message': "Action non autorisée"}, status=403)
    
    # Vérification expiration
    if reservation.is_expired():
        with transaction.atomic():
            reservation.status = Reservation.STATUS_CANCELLED
            reservation.save()
            for seat in reservation.seats.all():
                seat.status = Seat.STATUS_AVAILABLE
                seat.save()
        return JsonResponse({'success': False, 'message': "La réservation a expiré"}, status=400)
    
    # Vérification que le montant n'a pas été modifié
    amount = reservation.total_price
    if amount <= 0:
        logger.error(f"Invalid payment amount: {amount} for reservation {reservation_id}")
        return JsonResponse({'success': False, 'message': "Montant invalide"}, status=400)
    
    # Rate limiting sur les paiements
    rate_key = f"payment_{request.user.id}_{timezone.now().strftime('%Y%m%d%H')}"
    payment_count = cache.get(rate_key, 0)
    if payment_count >= 10:
        logger.warning(f"Payment rate limit exceeded for user {request.user.username}")
        return JsonResponse({'success': False, 'message': "Trop de tentatives. Veuillez réessayer plus tard."}, status=429)
    cache.set(rate_key, payment_count + 1, 3600)
    
    # ============================================================
    # MOBILE MONEY
    # ============================================================
    if payment_method in [Payment.METHOD_ORANGE, Payment.METHOD_MTN]:
        # Validation du numéro de téléphone
        if not phone_number or not phone_number.isdigit() or len(phone_number) < 8:
            return JsonResponse({'success': False, 'message': "Numéro de téléphone invalide"}, status=400)
        
        # Vérification qu'un paiement n'existe pas déjà
        existing_payment = Payment.objects.filter(
            reservation=reservation,
            status__in=[Payment.STATUS_PENDING, Payment.STATUS_SUCCESS]
        ).first()
        if existing_payment:
            return JsonResponse({'success': False, 'message': "Un paiement est déjà en cours"}, status=400)
        
        gateway = MobileMoneyMockGateway()
        res = gateway.initiate_transaction(phone_number, amount, 'EUR', payment_method)
        
        if res['success']:
            payment = Payment.objects.create(
                reservation=reservation,
                amount=amount,
                method=payment_method,
                status=Payment.STATUS_PENDING,
                transaction_id=res['transaction_id'],
                phone_number=phone_number,
                otp_code=res['otp'],
                gateway_logs=res['logs']
            )
            
            # Log de sécurité
            AuditLog.objects.create(
                user=request.user,
                action=f"Initiation paiement Mobile Money",
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Transaction: {payment.transaction_id}, Montant: {amount}€"
            )
            
            return JsonResponse({
                'success': True,
                'method': 'mobile_money',
                'transaction_id': payment.transaction_id,
                'message': f"Code OTP envoyé (pour le test, utilisez : {payment.otp_code})"
            })
        else:
            logger.error(f"Mobile money initiation failed: {res.get('logs')}")
            return JsonResponse({'success': False, 'message': "Erreur d'initiation"}, status=500)
    
    # ============================================================
    # CARTE BANCAIRE (Stripe mock)
    # ============================================================
    elif payment_method == Payment.METHOD_CARD:
        gateway = StripeMockGateway()
        res = gateway.process_charge(amount, 'EUR', reservation.id)
        
        if res['success']:
            with transaction.atomic():
                # Vérification anti-double paiement
                if reservation.status == Reservation.STATUS_CONFIRMED:
                    return JsonResponse({'success': False, 'message': "Déjà payé"}, status=400)
                
                Payment.objects.create(
                    reservation=reservation,
                    amount=amount,
                    method=payment_method,
                    status=Payment.STATUS_SUCCESS,
                    transaction_id=res['transaction_id'],
                    gateway_logs=res['logs']
                )
                
                reservation.status = Reservation.STATUS_CONFIRMED
                reservation.save()
                
                for seat in reservation.seats.all():
                    seat.status = Seat.STATUS_RESERVED
                    seat.save()
                
                AuditLog.objects.create(
                    user=request.user,
                    action=f"Paiement par carte validé",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Transaction: {res['transaction_id']}, Montant: {amount}€"
                )
                
            logger.info(f"Successful card payment: {res['transaction_id']} for user {request.user.username}")
            return JsonResponse({
                'success': True,
                'method': 'card',
                'redirect_url': '/dashboard/'
            })
        else:
            logger.error(f"Card payment failed: {res.get('logs')}")
            return JsonResponse({'success': False, 'message': "Paiement refusé"}, status=400)
    
    # ============================================================
    # PAYPAL
    # ============================================================
    elif payment_method == Payment.METHOD_PAYPAL:
        gateway = PayPalMockGateway()
        res = gateway.process_charge(amount, 'EUR', reservation.id)
        
        if res['success']:
            with transaction.atomic():
                if reservation.status == Reservation.STATUS_CONFIRMED:
                    return JsonResponse({'success': False, 'message': "Déjà payé"}, status=400)
                
                Payment.objects.create(
                    reservation=reservation,
                    amount=amount,
                    method=payment_method,
                    status=Payment.STATUS_SUCCESS,
                    transaction_id=res['transaction_id'],
                    gateway_logs=res['logs']
                )
                
                reservation.status = Reservation.STATUS_CONFIRMED
                reservation.save()
                
                for seat in reservation.seats.all():
                    seat.status = Seat.STATUS_RESERVED
                    seat.save()
                
                AuditLog.objects.create(
                    user=request.user,
                    action=f"Paiement PayPal validé",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Transaction: {res['transaction_id']}"
                )
                
            return JsonResponse({
                'success': True,
                'method': 'paypal',
                'redirect_url': '/dashboard/'
            })
        else:
            return JsonResponse({'success': False, 'message': "Paiement PayPal refusé"}, status=400)
    
    return JsonResponse({'success': False, 'message': "Moyen de paiement invalide"}, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def verify_otp(request):
    """
    Vérification OTP pour Mobile Money - AVEC VALIDATION
    """
    transaction_id = request.POST.get('transaction_id')
    user_otp = request.POST.get('otp', '').strip()
    
    if not transaction_id or not user_otp:
        return JsonResponse({'success': False, 'message': "Paramètres manquants"}, status=400)
    
    # Validation OTP (6 chiffres)
    if not user_otp.isdigit() or len(user_otp) != 6:
        return JsonResponse({'success': False, 'message': "Code OTP invalide (6 chiffres requis)"}, status=400)
    
    payment = get_object_or_404(Payment, transaction_id=transaction_id)
    reservation = payment.reservation
    
    # Vérification propriété
    if reservation.user != request.user:
        logger.error(f"OTP verification fraud attempt by {request.user.username} for payment {transaction_id}")
        return JsonResponse({'success': False, 'message': "Action non autorisée"}, status=403)
    
    # Vérification expiration
    if reservation.is_expired():
        payment.status = Payment.STATUS_FAILED
        payment.save()
        return JsonResponse({'success': False, 'message': "Réservation expirée"}, status=400)
    
    # Rate limiting sur les tentatives OTP
    otp_key = f"otp_{transaction_id}_{request.META.get('REMOTE_ADDR')}"
    otp_attempts = cache.get(otp_key, 0)
    if otp_attempts >= 3:
        logger.warning(f"OTP rate limit exceeded for transaction {transaction_id}")
        payment.status = Payment.STATUS_FAILED
        payment.save()
        return JsonResponse({'success': False, 'message': "Trop de tentatives. Transaction annulée."}, status=400)
    cache.set(otp_key, otp_attempts + 1, 300)
    
    gateway = MobileMoneyMockGateway()
    res = gateway.verify_otp(transaction_id, user_otp, payment.otp_code)
    
    if res['success']:
        with transaction.atomic():
            # Anti-double validation
            if payment.status == Payment.STATUS_SUCCESS:
                return JsonResponse({'success': False, 'message': "Déjà validé"}, status=400)
            
            payment.status = Payment.STATUS_SUCCESS
            payment.gateway_logs += f"\n{res['logs']}"
            payment.save()
            
            reservation.status = Reservation.STATUS_CONFIRMED
            reservation.save()
            
            for seat in reservation.seats.all():
                seat.status = Seat.STATUS_RESERVED
                seat.save()
            
            AuditLog.objects.create(
                user=request.user,
                action=f"Paiement Mobile Money validé par OTP",
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Transaction: {transaction_id}"
            )
            
        logger.info(f"Successful OTP verification for transaction {transaction_id}")
        return JsonResponse({
            'success': True,
            'message': "Paiement validé !",
            'redirect_url': '/dashboard/'
        })
    else:
        logger.warning(f"Failed OTP verification for transaction {transaction_id} from {request.META.get('REMOTE_ADDR')}")
        payment.status = Payment.STATUS_FAILED
        payment.gateway_logs += f"\n{res['logs']}"
        payment.save()
        return JsonResponse({'success': False, 'message': "Code OTP invalide"}, status=400)


def generate_tickets_for_reservation(reservation):
    """
    Génération sécurisée des tickets avec signature HMAC
    """
    secret_key = settings.SECRET_KEY.encode('utf-8')
    tickets = []
    
    for seat in reservation.seats.all():
        # Éviter les doublons si le ticket existe déjà
        if Ticket.objects.filter(reservation=reservation, seat=seat).exists():
            continue
            
        ticket_code = uuid.uuid4()
        
        # Message signé avec plus d'entropie
        message = (
            f"EVENT:{seat.event.id}"
            f"|SEAT:{seat.id}"
            f"|RES:{reservation.id}"
            f"|CODE:{ticket_code}"
            f"|TIME:{timezone.now().timestamp()}"
            f"|USER:{reservation.user.id if reservation.user else 'anonymous'}"
        )
        
        signature = hmac.new(secret_key, message.encode('utf-8'), hashlib.sha256).hexdigest()

        tickets.append(Ticket(
            reservation=reservation,
            seat=seat,
            ticket_code=ticket_code,
            qr_code_hash=signature,
            is_validated=False
        ))
    
    if tickets:
        Ticket.objects.bulk_create(tickets)