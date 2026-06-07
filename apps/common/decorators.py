"""
Décorateurs de sécurité pour les vues
Protection : Rate limiting, IP blocking, audit logging
"""

import functools
import logging
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache
from django.conf import settings
from functools import wraps
from administration.models import AuditLog

logger = logging.getLogger('security')


def rate_limit(limit=60, period=60, key_prefix='default'):
    """
    Décorateur de rate limiting
    Usage: @rate_limit(limit=10, period=60, key_prefix='api')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Générer la clé unique
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            key = f"rate_limit_{key_prefix}_{user_id}_{ip}"
            
            # Compter les requêtes
            current = cache.get(key, 0)
            
            if current >= limit:
                logger.warning(f"Rate limit {key_prefix} exceeded for {ip}")
                return JsonResponse({
                    'error': 'Too many requests',
                    'retry_after': period
                }, status=429)
            
            cache.set(key, current + 1, period)
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_ip_whitelist(allowed_ips=None):
    """
    Restreint l'accès à certaines IPs
    """
    if allowed_ips is None:
        allowed_ips = getattr(settings, 'ALLOWED_ADMIN_IPS', [])
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            client_ip = request.META.get('REMOTE_ADDR', '')
            
            if client_ip not in allowed_ips and not request.user.is_superuser:
                logger.warning(f"IP {client_ip} blocked from {request.path}")
                return HttpResponseForbidden("Accès non autorisé")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def audit_log(action_name):
    """
    Logge automatiquement l'action dans les logs d'audit
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            if request.user and request.user.is_authenticated:
                AuditLog.objects.create(
                    user=request.user,
                    action=action_name,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Path: {request.path}, Method: {request.method}"
                )
            
            return response
        
        return wrapper
    return decorator


def require_https(view_func):
    """
    Force HTTPS pour la vue
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return HttpResponseForbidden("HTTPS required")
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_post_only(view_func):
    """
    N'accepte que les requêtes POST
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        return view_func(request, *args, **kwargs)
    
    return wrapper


def prevent_csrf_bypass(view_func):
    """
    Vérification supplémentaire contre le contournement CSRF
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Vérifier le header Origin
        origin = request.META.get('HTTP_ORIGIN', '')
        host = request.META.get('HTTP_HOST', '')
        
        if origin and not origin.endswith(host):
            logger.warning(f"CSRF bypass attempt from origin {origin}")
            return HttpResponseForbidden("Invalid origin")
        
        # Vérifier le header Referer
        referer = request.META.get('HTTP_REFERER', '')
        if referer and not referer.startswith(f'http://{host}') and not referer.startswith(f'https://{host}'):
            logger.warning(f"CSRF bypass attempt from referer {referer}")
            return HttpResponseForbidden("Invalid referer")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper