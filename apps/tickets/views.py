"""
Dépend de:
- tickets/models.py (Ticket)
- common/security.py (RateLimiter)
"""

import qrcode
import qrcode.image.svg
from io import BytesIO
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from .models import Ticket
from common.security import RateLimiter


@cache_control(max_age=3600, public=True)
@require_http_methods(["GET"])
def generate_ticket_qr(request, ticket_code):
    """Génère un QR code SVG sécurisé"""
    ticket = get_object_or_404(Ticket, ticket_code=ticket_code)
    
    # Vérification d'accès
    if request.user.is_authenticated:
        is_owner = ticket.reservation.user == request.user
        is_admin = request.user.is_staff or request.user.is_admin()
        if not (is_owner or is_admin):
            return HttpResponse("Non autorisé", status=403)
    
    data = ticket.qr_code_hash
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(data, image_factory=factory, box_size=8, border=2)
    
    response = HttpResponse(content_type="image/svg+xml")
    img.save(response)
    return response


@login_required
@require_http_methods(["GET"])
def my_tickets(request):
    """Liste des tickets de l'utilisateur"""
    tickets = Ticket.objects.filter(
        reservation__user=request.user,
        reservation__status='CONFIRMED'
    ).select_related('seat', 'seat__event')
    
    return render(request, 'tickets/my_tickets.html', {'tickets': tickets})