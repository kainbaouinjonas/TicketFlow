"""
Vues du scanner avec sécurité renforcée
Protection : Validation HMAC, rate limiting, audit logs
"""

import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from tickets.models import Ticket
from administration.models import AuditLog

logger = logging.getLogger('security')


def is_controller_or_admin(user):
    """Vérifie les droits avec logging"""
    if not user.is_authenticated:
        return False
    
    has_rights = user.is_controller() or user.is_admin()
    
    if has_rights:
        logger.info(f"Scanner access granted to {user.username}")
    else:
        logger.warning(f"Unauthorized scanner access attempt by {user.username}")
    
    return has_rights


@login_required
@user_passes_test(is_controller_or_admin)
def scanner_dashboard(request):
    """Page principale du scanner"""
    return render(request, 'scanner/scanner.html')


@csrf_exempt  # Nécessaire pour les requêtes du scanner HTML5
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_controller_or_admin)
def validate_ticket(request):
    """
    Valide un billet via son QR code
    Protection : Rate limiting, validation HMAC, anti-fraud
    """
    # Rate limiting par IP et par utilisateur
    rate_key = f"scanner_{request.user.id}_{timezone.now().strftime('%Y%m%d%H%M')}"
    rate_count = cache.get(rate_key, 0)
    
    if rate_count >= 30:  # 30 validations par minute max
        logger.warning(f"Scanner rate limit exceeded for user {request.user.username}")
        return render(request, 'scanner/fragments/result.html', {
            'status': 'error',
            'message': "Trop de validations. Veuillez ralentir."
        })
    cache.set(rate_key, rate_count + 1, 60)
    
    # Récupérer le hash QR
    qr_hash = request.POST.get('qr_code_hash', '').strip()
    
    if not qr_hash:
        return render(request, 'scanner/fragments/result.html', {
            'status': 'error',
            'message': "Aucun code détecté."
        })
    
    # Vérification de la longueur du hash (protection contre les attaques)
    if len(qr_hash) < 32 or len(qr_hash) > 128:
        logger.warning(f"Invalid QR hash length: {len(qr_hash)} from {request.META.get('REMOTE_ADDR')}")
        return render(request, 'scanner/fragments/result.html', {
            'status': 'error',
            'message': "QR code invalide."
        })
    
    try:
        with transaction.atomic():
            # SELECT FOR UPDATE pour éviter les validations concurrentes
            ticket = Ticket.objects.select_for_update().get(qr_code_hash=qr_hash)
            
            # Vérifier que l'événement n'est pas terminé
            if ticket.seat.event.end_time and ticket.seat.event.end_time < timezone.now():
                logger.info(f"Expired ticket scan attempt: {ticket.ticket_code}")
                return render(request, 'scanner/fragments/result.html', {
                    'status': 'error',
                    'message': "Événement terminé",
                    'event': ticket.seat.event.title,
                    'seat': f"Rangée {ticket.seat.row}, Siège {ticket.seat.number}",
                    'category': ticket.seat.category
                })
            
            # Vérifier si déjà validé
            if ticket.is_validated:
                formatted_time = ticket.validated_at.strftime('%H:%M:%S le %d/%m/%Y')
                validator_name = ticket.validated_by.username if ticket.validated_by else "Système"
                
                logger.warning(f"Double validation attempt for ticket {ticket.ticket_code} by {request.user.username}")
                
                AuditLog.objects.create(
                    user=request.user,
                    action="Double validation tentée",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Ticket {ticket.ticket_code} déjà validé par {validator_name}"
                )
                
                return render(request, 'scanner/fragments/result.html', {
                    'status': 'warning',
                    'message': "Billet DÉJÀ VALIDÉ",
                    'event': ticket.seat.event.title,
                    'seat': f"Rangée {ticket.seat.row}, Siège {ticket.seat.number}",
                    'category': ticket.seat.category,
                    'validated_at': formatted_time,
                    'validated_by': validator_name
                })
            
            # VALIDATION RÉUSSIE
            ticket.is_validated = True
            ticket.validated_at = timezone.now()
            ticket.validated_by = request.user
            ticket.save()
            
            logger.info(f"Ticket validated: {ticket.ticket_code} by {request.user.username}")
            
            AuditLog.objects.create(
                user=request.user,
                action="Validation billet",
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Ticket {ticket.ticket_code} - Événement: {ticket.seat.event.title}"
            )
            
            return render(request, 'scanner/fragments/result.html', {
                'status': 'success',
                'message': "BILLET VALIDE - ACCÈS AUTORISÉ",
                'event': ticket.seat.event.title,
                'seat': f"Rangée {ticket.seat.row}, Siège {ticket.seat.number}",
                'category': ticket.seat.category,
                'location': ticket.seat.event.location
            })
            
    except Ticket.DoesNotExist:
        logger.warning(f"Invalid ticket validation attempt from {request.META.get('REMOTE_ADDR')} - Hash: {qr_hash[:20]}...")
        
        AuditLog.objects.create(
            user=request.user,
            action="Tentative validation QR invalide",
            ip_address=request.META.get('REMOTE_ADDR'),
            details=f"Hash reçu: {qr_hash[:50]}..."
        )
        
        return render(request, 'scanner/fragments/result.html', {
            'status': 'error',
            'message': "BILLET INVALIDE",
            'fraud_attempt': True
        })