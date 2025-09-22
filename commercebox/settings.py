"""
CommerceBox - Sistema de Inventario Comercial Dual
Configuración principal de Django
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('COMMERCEBOX_SECRET_KEY', default='django-insecure-commercebox-development-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('COMMERCEBOX_DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('COMMERCEBOX_ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_extensions',
]

COMMERCEBOX_APPS = [
    'apps.authentication',
    'apps.inventory_management',
    'apps.sales_management',
    'apps.financial_management',
    'apps.reports_analytics',
    'apps.hardware_integration',
    'apps.notifications',
    'apps.system_configuration',
    'apps.custom_admin',
    'apps.stock_alert_system',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + COMMERCEBOX_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'commercebox.urls'

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

WSGI_APPLICATION = 'commercebox.wsgi.application'

# Database Configuration
if config('COMMERCEBOX_USE_SQLITE', default=False, cast=bool):
    # SQLite para desarrollo rápido
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # PostgreSQL para producción y desarrollo completo
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('COMMERCEBOX_DB_NAME', default='commercebox'),
            'USER': config('COMMERCEBOX_DB_USER', default='commercebox_user'),
            'PASSWORD': config('COMMERCEBOX_DB_PASSWORD', default=''),
            'HOST': config('COMMERCEBOX_DB_HOST', default='localhost'),
            'PORT': config('COMMERCEBOX_DB_PORT', default='5432'),
        }
    }

# Usuario personalizado
AUTH_USER_MODEL = 'authentication.Usuario'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-ES'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}

# Celery Configuration
CELERY_BROKER_URL = config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# CommerceBox Specific Settings
COMMERCEBOX_SETTINGS = {
    'SYSTEM_NAME': 'CommerceBox',
    'VERSION': '1.0.0',
    'CODIGO_PREFIJO_QUINTAL': 'CBX-QNT',
    'CODIGO_PREFIJO_PRODUCTO': 'CBX-PRD',
    'NUMERO_FACTURA_PREFIJO': 'CBX',
    'BACKUP_ENABLED': config('COMMERCEBOX_BACKUP_ENABLED', default=True, cast=bool),
    'ALERTAS_STOCK_ENABLED': config('COMMERCEBOX_ALERTAS_ENABLED', default=True, cast=bool),
    'FACTURACION_ELECTRONICA_ENABLED': config('COMMERCEBOX_FE_ENABLED', default=False, cast=bool),
    'MAX_DESCUENTO_SIN_AUTORIZACION': 10.0,  # Porcentaje
    'DIAS_VENCIMIENTO_ALERTA': 30,
    'PESO_MINIMO_QUINTAL_CRITICO': 5.0,  # kg
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'commercebox.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'audit': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'commercebox_audit.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'commercebox': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'commercebox.audit': {
            'handlers': ['audit'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True

# Login/Logout URLs
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Email Configuration (opcional)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@commercebox.com')

# Security settings
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Session Configuration
SESSION_COOKIE_AGE = config('COMMERCEBOX_SESSION_TIMEOUT', default=3600, cast=int)  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True