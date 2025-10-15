"""
CommerceBox - Sistema de Inventario Comercial Dual
Configuración principal de Django
"""

import os
from pathlib import Path
from datetime import timedelta
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
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_extensions',
    'django_filters',
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
                'apps.context_processors.system_config',
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
        'OPTIONS': {
            'min_length': 8,
        }
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
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

# Simple JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'commercebox',
    'JWK_URL': None,
    'LEEWAY': 0,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ============================================================================
# CONFIGURACIÓN DE CELERY - COMPLETA Y MEJORADA
# ============================================================================

# Importar crontab para tareas programadas
from celery.schedules import crontab

# -------- CONFIGURACIÓN DEL BROKER Y BACKEND --------
CELERY_BROKER_URL = config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/0')

# -------- SERIALIZACIÓN --------
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# -------- ZONA HORARIA --------
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# -------- CONFIGURACIÓN DE TAREAS --------
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos límite máximo
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos límite suave (advertencia)
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 5 * 60  # 5 minutos entre reintentos

# -------- CONFIGURACIÓN DE RESULTADOS --------
CELERY_RESULT_EXPIRES = 3600  # Los resultados expiran después de 1 hora
CELERY_RESULT_PERSISTENT = True  # Persistir resultados en Redis
CELERY_IGNORE_RESULT = False  # No ignorar resultados (queremos guardarlos)

# -------- OPTIMIZACIÓN Y RENDIMIENTO --------
CELERY_WORKER_PREFETCH_MULTIPLIER = 4  # Número de tareas a pre-cargar por worker
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Reiniciar worker después de 1000 tareas
CELERY_TASK_ACKS_LATE = True  # Reconocer tarea solo después de completarla
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Rechazar tarea si el worker falla

# -------- CONFIGURACIÓN DE REDIS --------
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# -------- CONFIGURACIÓN DE LOGS --------
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# -------- CELERY BEAT SCHEDULER (Tareas Programadas) --------
# Si quieres usar django-celery-beat (base de datos para tareas programadas)
# Descomenta las siguientes líneas y agrega 'django_celery_beat' a INSTALLED_APPS
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# -------- TAREAS PROGRAMADAS --------
CELERY_BEAT_SCHEDULE = {
    # Verificar alertas de stock cada 30 minutos
    'check-stock-alerts': {
        'task': 'apps.stock_alert_system.tasks.check_stock_alerts',
        'schedule': crontab(minute='*/30'),
        'options': {
            'expires': 15 * 60,  # La tarea expira en 15 minutos si no se ejecuta
        }
    },
    
    # Ejemplo: Generar reporte diario a las 00:00
    # 'generate-daily-report': {
    #     'task': 'apps.reports_analytics.tasks.generate_daily_report',
    #     'schedule': crontab(hour=0, minute=0),
    #     'options': {
    #         'expires': 3600,
    #     }
    # },
    
    # Ejemplo: Limpiar sesiones expiradas cada domingo a las 3:00 AM
    # 'cleanup-expired-sessions': {
    #     'task': 'apps.authentication.tasks.cleanup_expired_sessions',
    #     'schedule': crontab(hour=3, minute=0, day_of_week=0),
    # },
    
    # Ejemplo: Enviar alertas de productos por vencer cada día a las 9:00 AM
    # 'send-expiration-alerts': {
    #     'task': 'apps.inventory_management.tasks.send_expiration_alerts',
    #     'schedule': crontab(hour=9, minute=0),
    # },
}

# -------- CONFIGURACIÓN DE MONITOREO --------
CELERY_SEND_TASK_ERROR_EMAILS = False  # Cambiar a True en producción
CELERY_SEND_TASK_SENT_EVENT = True  # Enviar eventos cuando se envía una tarea

# -------- CONFIGURACIÓN DE SEGURIDAD --------
CELERY_TASK_ALWAYS_EAGER = False  # False en producción, True solo para testing
# Si CELERY_TASK_ALWAYS_EAGER = True, las tareas se ejecutan síncronamente (útil para tests)

# ============================================================================
# FIN DE CONFIGURACIÓN DE CELERY
# ============================================================================

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
# Crear directorio de logs si no existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

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
            'filename': LOGS_DIR / 'commercebox.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'audit': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'commercebox_audit.log',
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

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================================================
# CONFIGURACIÓN DE LOGIN Y REDIRECCIÓN
# ============================================================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/panel/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Email Configuration
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
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True

# Session Configuration
SESSION_COOKIE_AGE = config('COMMERCEBOX_SESSION_TIMEOUT', default=3600, cast=int)  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'commercebox',
        'TIMEOUT': 300,
    }
}

# Password Reset Configuration
PASSWORD_RESET_TIMEOUT = 3600  # 1 hora en segundos

# ============================================================================
# CONFIGURACIÓN ESPECÍFICA PARA INVENTORY_MANAGEMENT
# ============================================================================

# Crear directorios necesarios
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'barcodes'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'barcodes', 'quintales'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'barcodes', 'productos'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'productos'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'invoices'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'reports'), exist_ok=True)

# Configuración de límites de archivos
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Formato de números decimales
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ','
DECIMAL_SEPARATOR = '.'
NUMBER_GROUPING = 3