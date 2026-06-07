from django.urls import path
from .views import generate_ticket_qr, my_tickets

urlpatterns = [
    path('qr/<uuid:ticket_code>/', generate_ticket_qr, name='ticket_qr'),
    path('my-tickets/', my_tickets, name='my_tickets'),
]