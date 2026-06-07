"""
Context processors pour les templates sécurisés
"""

from django.conf import settings


def security_headers(request):
    """
    Ajoute les en-têtes de sécurité aux contextes de template
    """
    return {
        'CSP_NONCE': request.csp_nonce if hasattr(request, 'csp_nonce') else '',
        'DEBUG': settings.DEBUG,
        'SECURE_SSL_REDIRECT': settings.SECURE_SSL_REDIRECT,
    }


def csrf_token(request):
    """
    Fournit le token CSRF avec des informations supplémentaires
    """
    return {
        'csrf_token': request.COOKIES.get('csrftoken', ''),
        'csrf_token_safe': request.META.get('CSRF_COOKIE', ''),
    }


def user_permissions(request):
    """
    Permissions utilisateur pour les templates
    """
    if not request.user.is_authenticated:
        return {'user_permissions': []}
    
    perms = []
    if request.user.is_admin():
        perms.append('admin')
    if request.user.is_controller():
        perms.append('controller')
    if request.user.is_organizer():
        perms.append('organizer')
    
    return {'user_permissions': perms}