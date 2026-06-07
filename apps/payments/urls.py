from django.urls import path
from .views import checkout, process_payment, verify_otp

urlpatterns = [
    path('checkout/<int:reservation_id>/', checkout, name='checkout'),
    path('process/', process_payment, name='process_payment'),
    path('verify-otp/', verify_otp, name='verify_otp'),
]