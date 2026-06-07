from django.urls import path
from .views import scanner_dashboard, validate_ticket

urlpatterns = [
    path('', scanner_dashboard, name='scanner'),
    path('validate/', validate_ticket, name='validate_ticket'),
]