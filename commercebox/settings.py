"""
CommerceBox - Sistema de Inventario Comercial Dual
Configuración principal de Django

🔧 ARCHIVO CORREGIDO - Versión con solución para sesiones y autenticación
Fecha: 2025-10-18
Cambios: CORS, CSRF, ALLOWED_HOSTS, SESIONES configurados correctamente
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

# ============================================================================
# 🔧 CORRECCIÓN 1: ALLOWED_HOSTS - Permitir acceso desde cualquier IP
# ============================================================================
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '*',  # ⚠️ Permite TODAS las IPs - SOLO PARA DESARROLLO
]

# Para producción, usar lista específica:
# ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.1.100', 'tudominio.com']

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
    'rest_framework.authtoken',
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

# ============================================================================
# 🔧 CORRECCIÓN 2: MIDDLEWARE - Agregar CsrfExemptAgenteMiddleware
# ============================================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ✅ Debe estar primero
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.authentication.middleware.DualAuthenticationMiddleware',  # Autenticación dual JWT + Sessions
    # 🆕 AGREGADO: Middleware para leer JWT desde cookies HTTP-only
    'apps.authentication.middleware.JWTAuthFromCookieMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware para excluir CSRF del agente
    'apps.hardware_integration.middleware.CsrfExemptAgenteMiddleware',
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

# ============================================================================
# 🔧 CORRECCIÓN 3: REST FRAMEWORK - Asegurar TokenAuthentication
# ============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',  # ✅ Requerido para el agente
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
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour',  
        'agente': None,  # Sin límite para el agente
    }
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
# CONFIGURACIÓN DE CELERY PARA TAREAS ASÍNCRONAS
# ============================================================================

# URL del broker de mensajes (Redis)
CELERY_BROKER_URL = config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/0')

# URL del backend de resultados (Redis)
CELERY_RESULT_BACKEND = config('COMMERCEBOX_REDIS_URL', default='redis://localhost:6379/0')

# Formato de serialización
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Configuración de tareas
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos

# Configuración de workers
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100

# Beat Schedule (Tareas periódicas)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'verificar-alertas-stock': {
        'task': 'apps.stock_alert_system.tasks.verificar_alertas_stock',
        'schedule': crontab(minute='*/15'),
        'options': {
            'expires': 10 * 60,
        }
    },
    'procesar-notificaciones-pendientes': {
        'task': 'apps.notifications.tasks.procesar_notificaciones_pendientes',
        'schedule': crontab(minute='*/5'),
        'options': {
            'expires': 4 * 60,
        }
    },
    'limpiar-sesiones-expiradas': {
        'task': 'apps.authentication.tasks.limpiar_sesiones_expiradas',
        'schedule': crontab(hour=3, minute=0),
        'options': {
            'expires': 30 * 60,
        }
    },
    'generar-reporte-ventas-diario': {
        'task': 'apps.reports_analytics.tasks.generar_reporte_ventas_diario',
        'schedule': crontab(hour=23, minute=30),
        'options': {
            'expires': 15 * 60,
        }
    },
}

# Monitoreo
CELERY_SEND_TASK_ERROR_EMAILS = False
CELERY_SEND_TASK_SENT_EVENT = True

# Seguridad
CELERY_TASK_ALWAYS_EAGER = False

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

# ============================================================================
# 🔧 CORRECCIÓN 4: CONFIGURACIÓN DE CORS - COMPLETA Y CORREGIDA
# ============================================================================

# Orígenes específicos permitidos
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]

# Permitir peticiones desde la red local usando regex
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$",  # Redes 192.168.x.x
    r"^http://172\.16\.\d{1,3}\.\d{1,3}(:\d+)?$",   # Docker (172.16.x.x)
    r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$",  # Otras redes privadas (10.x.x.x)
]

# Permitir cookies y autenticación en peticiones CORS
CORS_ALLOW_CREDENTIALS = True

# Métodos HTTP permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Headers permitidos en peticiones CORS
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
    'X-CSRFToken',
]

# ============================================================================
# 🔧 CORRECCIÓN 5: CSRF_TRUSTED_ORIGINS - Permitir red local
# ============================================================================

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
]

# ============================================================================
# CONFIGURACIÓN DE LOGIN Y REDIRECCIÓN
# ============================================================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/panel/'
LOGOUT_REDIRECT_URL = '/login/'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@commercebox.com')

# ============================================================================
# 🔧 CORRECCIÓN 6: CONFIGURACIÓN DE SESIONES - CRÍTICO PARA AUTENTICACIÓN
# ============================================================================

# Security settings - Solo aplicar en producción
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

# ✅ CONFIGURACIÓN DE SESIONES - CORREGIDA PARA DESARROLLO
# Estas configuraciones DEBEN estar DESPUÉS del bloque "if not DEBUG"
# para que no sean sobrescritas

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'sessionid'  # ← Asegúrate que sea 'sessionid', no otro nombre
SESSION_COOKIE_HTTPONLY = False  # ← Temporalmente en False para debug
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_DOMAIN = None  # ← AGREGA ESTA LÍNEA
SESSION_COOKIE_PATH = '/'  # ← AGREGA ESTA LÍNEA

# ⚠️ IMPORTANTE: En producción, cambiar a:
# SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SECURE = True

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

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
