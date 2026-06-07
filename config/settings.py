import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Charge les variables depuis .env (si présent)
load_dotenv()

# Python 3.14 compatibility hotfix for Django template context copy bug
# Python 3.14 changed how super().__copy__ works, breaking Django's template context.
try:
    import django.template.context as _dtc

    def _make_patched_copy(cls_name):
        def patched_copy(self):
            cls = self.__class__
            duplicate = cls.__new__(cls)
            duplicate.__dict__.update(self.__dict__)
            if hasattr(self, 'dicts'):
                duplicate.dicts = self.dicts[:]
            if hasattr(self, 'render_context'):
                duplicate.render_context = self.render_context
            return duplicate
        patched_copy.__qualname__ = f'{cls_name}.__copy__'
        return patched_copy

    for _ctx_cls_name in ('BaseContext', 'Context', 'RenderContext', 'RequestContext'):
        _ctx_cls = getattr(_dtc, _ctx_cls_name, None)
        if _ctx_cls is not None:
            _ctx_cls.__copy__ = _make_patched_copy(_ctx_cls_name)
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# ============================================================
# CLÉ SECRÈTE
# ============================================================
SECRET_KEY = 'django-insecure-temp-key-8a7f3d9c2e1b5a4d6f8g7h6j5k4l3m2n1'

DEBUG = True
ALLOWED_HOSTS = ['*']

# ============================================================
# INSTALLED APPS
# ============================================================
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'channels_redis',
    'crispy_forms',
    'crispy_tailwind',
    'django_prometheus',
    'django_celery_beat',
    'django_celery_results',
    'axes',
    'common',
    'authentication',
    'administration',
    'events',
    'reservations',
    'payments',
    'tickets',
    'websocket',
    'scanner',
    'dashboard',
    'monitoring',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'common.middleware.AuditLogMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
    ('de', 'Deutsch'),
    ('zh', 'Chinese'),
    ('es', 'Español'),
    ('pt', 'Português'),
    ('ar', 'Arabic'),
]


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ============================================================
# BASE DE DONNÉES — PostgreSQL (toujours)
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'ticket_platform'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

AUTH_USER_MODEL = 'authentication.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

STRIPE_PUBLIC_KEY = 'pk_test_mock'
STRIPE_SECRET_KEY = 'sk_test_mock'

# Email Backend (console en développement)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@ticketflow.fr'

# Cache et Channels (Redis sous Docker, Local/Memory en dev)
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ticketflow-cache',
        }
    }
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# Axes (brute-force protection)
AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = 1  # heures
AXES_LOCKOUT_CALLABLE = None

# Celery Configuration Options
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


