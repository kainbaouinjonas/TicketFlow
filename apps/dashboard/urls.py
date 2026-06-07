from django.urls import path
from .views import user_dashboard, check_pending_reservations, order_history, profile

urlpatterns = [
    path('', user_dashboard, name='dashboard'),
    path('check-pending/', check_pending_reservations, name='check_pending'),
    path('order-history/', order_history, name='order_history'),
    path('profile/', profile, name='profile'),
]