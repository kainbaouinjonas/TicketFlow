from django.urls import path
from .views import add_to_cart, remove_from_cart, cart_detail, create_reservation, cart_count

urlpatterns = [
    path('cart/', cart_detail, name='cart_detail'),
    path('cart/count/', cart_count, name='cart_count'),
    path('cart/add/<int:seat_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:seat_id>/', remove_from_cart, name='remove_from_cart'),
    path('create/', create_reservation, name='create_reservation'),
]