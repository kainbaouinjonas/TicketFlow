from django.urls import path
from .views import (
    admin_dashboard, event_create, event_update, event_delete,
    audit_logs, chart_data, approve_organizer,
    list_controllers, create_controller, delete_controller
)

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('event/create/', event_create, name='event_create'),
    path('event/<int:pk>/update/', event_update, name='event_update'),
    path('event/<int:pk>/delete/', event_delete, name='event_delete'),
    path('logs/', audit_logs, name='admin_logs'),
    path('chart-data/', chart_data, name='admin_chart_data'),
    path('organizer/<int:user_id>/approve/', approve_organizer, name='approve_organizer'),
    path('controllers/', list_controllers, name='list_controllers'),
    path('controllers/create/', create_controller, name='create_controller'),
    path('controllers/<int:user_id>/delete/', delete_controller, name='delete_controller'),
]