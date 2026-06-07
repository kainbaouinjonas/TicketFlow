from django.urls import re_path
from .consumers import SeatMapConsumer

websocket_urlpatterns = [
    re_path(r'ws/events/(?P<event_id>\d+)/$', SeatMapConsumer.as_asgi()),
]