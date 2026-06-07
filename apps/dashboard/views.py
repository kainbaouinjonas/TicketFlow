from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reservations.models import Reservation
from tickets.models import Ticket
from payments.models import Payment


@login_required
@require_http_methods(["GET"])
def user_dashboard(request):
    # Routage basé sur les rôles
    if request.user.role in ['ORGANIZER', 'ADMIN'] or request.user.is_superuser:
        from django.shortcuts import redirect
        return redirect('admin_dashboard')
        
    if request.user.role == 'CONTROLLER':
        from administration.models import AuditLog
        today = timezone.now().date()
        validations_count = AuditLog.objects.filter(
            user=request.user,
            action="Validation billet",
            timestamp__date=today
        ).count()
        
        recent_validations = AuditLog.objects.filter(
            user=request.user,
            action="Validation billet"
        ).order_by('-timestamp')[:10]
        
        return render(request, 'dashboard/controller_dashboard.html', {
            'validations_count': validations_count,
            'recent_validations': recent_validations,
        })

    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    
    tickets = Ticket.objects.filter(
        reservation__user=request.user,
        reservation__status=Reservation.STATUS_CONFIRMED
    ).select_related('seat', 'seat__event')
    
    total_spent = sum(p.amount for p in Payment.objects.filter(
        reservation__user=request.user,
        status=Payment.STATUS_SUCCESS
    ))
    
    loyalty_points = int(total_spent // 10) if total_spent else 0
    
    return render(request, 'dashboard/user_dashboard.html', {
        'reservations': reservations,
        'tickets': tickets,
        'total_spent': total_spent,
        'loyalty_points': loyalty_points,
    })


@login_required
@require_http_methods(["GET"])
def check_pending_reservations(request):
    has_pending = Reservation.objects.filter(
        user=request.user,
        status=Reservation.STATUS_PENDING,
        expires_at__gt=timezone.now()
    ).exists()
    return JsonResponse({'has_pending': has_pending})


@login_required
@require_http_methods(["GET"])
def order_history(request):
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/order_history.html', {'reservations': reservations})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        # Update phone_number if custom field exists
        if hasattr(user, 'phone_number'):
            user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.save()
        from django.contrib import messages
        messages.success(request, "Votre profil a été mis à jour.")
        
    return render(request, 'dashboard/profile.html', {'user': request.user})