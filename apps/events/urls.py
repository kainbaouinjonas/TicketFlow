from django.urls import path
from .views import EventListView, EventDetailView, event_seat_map

urlpatterns = [
    path('', EventListView.as_view(), name='home'),
    path('events/', EventListView.as_view(), name='events'),
    path('events/<slug:slug>/', EventDetailView.as_view(), name='event_detail'),
    path('events/<slug:slug>/seats/', event_seat_map, name='event_seat_map'),
]