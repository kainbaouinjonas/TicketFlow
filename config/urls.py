from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'healthy', 'debug': settings.DEBUG})

def readiness_check(request):
    return JsonResponse({'status': 'ready'})

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('django-admin/', admin.site.urls),
    path('', include('events.urls')),
    path('auth/', include('authentication.urls')),
    path('reservations/', include('reservations.urls')),
    path('payments/', include('payments.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('scanner/', include('scanner.urls')),
    path('admin-dashboard/', include('administration.urls')),
    path('metrics/', include('monitoring.urls')),
    path('tickets/', include('tickets.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)