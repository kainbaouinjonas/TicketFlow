from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from events.models import Event, Seat
from .forms import EventForm, ControllerCreateForm
from .models import AuditLog
from reservations.models import Reservation
from payments.models import Payment

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'ADMIN')


def is_admin_or_organizer(user):
    return user.is_authenticated and (user.is_superuser or user.role in ['ADMIN', 'ORGANIZER'])


def _get_event_stats(events):
    """Calcule les statistiques de remplissage pour chaque événement."""
    result = []
    for event in events:
        total_seats = event.seats.count()
        sold_seats = event.seats.filter(status=Seat.STATUS_RESERVED).count()
        fill_rate = round((sold_seats / total_seats * 100), 1) if total_seats > 0 else 0
        result.append({
            'event': event,
            'total_seats': total_seats,
            'sold_seats': sold_seats,
            'fill_rate': fill_rate,
        })
    return result


@login_required
@user_passes_test(is_admin_or_organizer)
def admin_dashboard(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    is_global_admin = request.user.is_superuser or request.user.role == 'ADMIN'

    pending_organizers = None
    if is_global_admin:
        events = Event.objects.all().select_related('category', 'organizer').prefetch_related('seats')
        
        total_revenue = Payment.objects.filter(status=Payment.STATUS_SUCCESS).aggregate(
            total=Sum('amount')
        )['total'] or 0

        total_sales = Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED).count()
        total_users = User.objects.filter(is_active=True).count()
        active_locks = Seat.objects.filter(status=Seat.STATUS_LOCKED).count()
        latest_reservations = Reservation.objects.select_related('user').order_by('-created_at')[:10]
        pending_organizers = User.objects.filter(role='ORGANIZER', is_active=False).order_by('-date_joined')
    else:
        events = Event.objects.filter(organizer=request.user).select_related('category', 'organizer').prefetch_related('seats')
        
        total_revenue = Payment.objects.filter(
            status=Payment.STATUS_SUCCESS,
            reservation__seats__event__organizer=request.user
        ).distinct().aggregate(total=Sum('amount'))['total'] or 0

        total_sales = Reservation.objects.filter(
            status=Reservation.STATUS_CONFIRMED,
            seats__event__organizer=request.user
        ).distinct().count()

        total_users = User.objects.filter(
            reservations__seats__event__organizer=request.user
        ).distinct().count()

        active_locks = Seat.objects.filter(
            status=Seat.STATUS_LOCKED,
            event__organizer=request.user
        ).count()

        latest_reservations = Reservation.objects.filter(
            seats__event__organizer=request.user
        ).select_related('user').distinct().order_by('-created_at')[:10]

    events_with_stats = _get_event_stats(events)

    return render(request, 'admin/dashboard.html', {
        'events': events_with_stats,
        'total_revenue': total_revenue,
        'total_sales': total_sales,
        'total_users': total_users,
        'active_locks': active_locks,
        'latest_reservations': latest_reservations,
        'pending_organizers': pending_organizers,
    })


@login_required
@user_passes_test(is_admin_or_organizer)
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

            # Générer les sièges automatiquement selon la capacité
            _generate_seats_for_event(event)

            messages.success(request, f"Événement '{event.title}' créé avec ses sièges !")
            return redirect('admin_dashboard')
    else:
        form = EventForm()
    return render(request, 'admin/event_form.html', {'form': form, 'title': "Créer un événement"})


def _generate_seats_for_event(event):
    """Génère les sièges pour un événement selon sa capacité."""
    if event.seats.exists():
        return  # Déjà des sièges

    capacity = event.total_capacity
    # Répartition : 10% VIP, 30% GOLD, 60% STANDARD
    vip_count = max(1, int(capacity * 0.10))
    gold_count = max(1, int(capacity * 0.30))
    std_count = capacity - vip_count - gold_count

    base_price = float(event.price) if event.price > 0 else 25.00
    vip_price = round(base_price * 4.8, 2)
    gold_price = round(base_price * 2.4, 2)
    std_price = round(base_price, 2)

    seats = []
    seat_num = 1

    # Rangées VIP
    row_letter = 65  # 'A'
    remaining = vip_count
    while remaining > 0:
        seats_in_row = min(10, remaining)
        for n in range(1, seats_in_row + 1):
            seats.append(Seat(
                event=event,
                row=chr(row_letter),
                number=n,
                category=Seat.SEAT_VIP,
                price=vip_price,
                status=Seat.STATUS_AVAILABLE
            ))
        remaining -= seats_in_row
        row_letter += 1

    # Rangées GOLD
    remaining = gold_count
    while remaining > 0:
        seats_in_row = min(10, remaining)
        for n in range(1, seats_in_row + 1):
            seats.append(Seat(
                event=event,
                row=chr(row_letter),
                number=n,
                category=Seat.SEAT_GOLD,
                price=gold_price,
                status=Seat.STATUS_AVAILABLE
            ))
        remaining -= seats_in_row
        row_letter += 1

    # Rangées STANDARD
    remaining = std_count
    while remaining > 0:
        seats_in_row = min(10, remaining)
        for n in range(1, seats_in_row + 1):
            seats.append(Seat(
                event=event,
                row=chr(row_letter),
                number=n,
                category=Seat.SEAT_STANDARD,
                price=std_price,
                status=Seat.STATUS_AVAILABLE
            ))
        remaining -= seats_in_row
        row_letter += 1

    Seat.objects.bulk_create(seats)


@login_required
@user_passes_test(is_admin_or_organizer)
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    is_global_admin = request.user.is_superuser or request.user.role == 'ADMIN'
    if not is_global_admin and event.organizer != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier cet événement.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Événement '{event.title}' mis à jour !")
            return redirect('admin_dashboard')
    else:
        form = EventForm(instance=event)
    return render(request, 'admin/event_form.html', {'form': form, 'title': f"Modifier {event.title}"})


@login_required
@user_passes_test(is_admin_or_organizer)
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    is_global_admin = request.user.is_superuser or request.user.role == 'ADMIN'
    if not is_global_admin and event.organizer != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer cet événement.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        title = event.title
        event.delete()
        messages.warning(request, f"Événement '{title}' supprimé.")
        return redirect('admin_dashboard')
    return render(request, 'admin/event_confirm_delete.html', {'event': event})


@login_required
@user_passes_test(is_admin)
def audit_logs(request):
    logs_qs = AuditLog.objects.select_related('user').order_by('-timestamp')

    # Filtres
    user_filter = request.GET.get('user', '').strip()
    action_filter = request.GET.get('action', '').strip()
    if user_filter:
        logs_qs = logs_qs.filter(user__username__icontains=user_filter)
    if action_filter:
        logs_qs = logs_qs.filter(action__icontains=action_filter)

    paginator = Paginator(logs_qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/audit_logs.html', {
        'logs': page_obj,
        'is_paginated': paginator.num_pages > 1,
    })


@login_required
@user_passes_test(is_admin_or_organizer)
def chart_data(request):
    """Retourne les données de ventes des 6 derniers mois pour le graphique."""
    from datetime import date
    from django.db.models.functions import TruncMonth

    monthly_data = (
        Payment.objects
        .filter(status=Payment.STATUS_SUCCESS)
    )
    is_global_admin = request.user.is_superuser or request.user.role == 'ADMIN'
    if not is_global_admin:
        monthly_data = monthly_data.filter(reservation__seats__event__organizer=request.user)

    monthly_data = (
        monthly_data
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )

    labels = []
    revenue = []
    for entry in list(monthly_data)[-6:]:
        labels.append(entry['month'].strftime('%b %Y'))
        revenue.append(float(entry['total']))

    return JsonResponse({'labels': labels, 'revenue': revenue})


@login_required
@user_passes_test(is_admin)
def list_controllers(request):
    """Liste et gestion des contrôleurs"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    controllers = User.objects.filter(role='CONTROLLER').order_by('-date_joined')
    return render(request, 'admin/controllers.html', {'controllers': controllers})


@login_required
@user_passes_test(is_admin)
def create_controller(request):
    """Créer un nouveau compte contrôleur"""
    if request.method == 'POST':
        form = ControllerCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'CONTROLLER'
            user.is_active = True
            user.save()

            AuditLog.objects.create(
                user=request.user,
                action="Création compte Contrôleur",
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Contrôleur créé : {user.username}"
            )

            messages.success(request, f"Contrôleur '{user.username}' créé avec succès !")
            return redirect('list_controllers')
    else:
        form = ControllerCreateForm()
    return render(request, 'admin/create_controller.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def delete_controller(request, user_id):
    """Supprimer / désactiver un contrôleur"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    controller = get_object_or_404(User, id=user_id, role='CONTROLLER')
    if request.method == 'POST':
        username = controller.username
        controller.is_active = False
        controller.save()
        AuditLog.objects.create(
            user=request.user,
            action="Désactivation contrôleur",
            ip_address=request.META.get('REMOTE_ADDR'),
            details=f"Contrôleur désactivé : {username}"
        )
        messages.warning(request, f"Contrôleur '{username}' désactivé.")
    return redirect('list_controllers')


@login_required
@user_passes_test(is_admin)
def approve_organizer(request, user_id):
    """Approuve et active un compte organisateur"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    organizer = get_object_or_404(User, id=user_id, role='ORGANIZER')
    organizer.is_active = True
    organizer.save()

    # Log de sécurité
    AuditLog.objects.create(
        user=request.user,
        action="Approbation Organisateur",
        ip_address=request.META.get('REMOTE_ADDR'),
        details=f"Compte organisateur activé : {organizer.username}"
    )

    messages.success(request, f"L'organisateur '{organizer.username}' a été approuvé avec succès !")
    return redirect('admin_dashboard')

