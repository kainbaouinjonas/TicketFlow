from django.http import HttpResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge
from events.models import Seat
from reservations.models import Reservation
from payments.models import Payment

# Define Prometheus metrics
RESERVATIONS_CONFIRMED = Counter('reservations_confirmed_total', 'Total number of confirmed reservations')
SEATS_LOCKED = Gauge('seats_locked_current', 'Current number of locked seats in the system')
REVENUE_TOTAL = Counter('platform_revenue_total_eur', 'Total revenue generated in EUR')

def metrics_view(request):
    # Dynamically update Gauges
    SEATS_LOCKED.set(Seat.objects.filter(status=Seat.STATUS_LOCKED).count())
    
    # We can also track confirmed reservations and update counter
    confirmed_count = Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED).count()
    
    # Total successful payment amounts
    total_rev = sum(p.amount for p in Payment.objects.filter(status=Payment.STATUS_SUCCESS))
    
    # Build Prometheus response
    data = generate_latest()
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
