"""
Middleware personalizado para el módulo de autenticación
"""
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import LogAcceso, SesionUsuario
from .decorators import get_client_ip
import logging

logger = logging.getLogger('apps.authentication')
Usuario = get_user_model()


class JWTAuthenticationMiddleware:
    """
    Middleware para tracking de autenticación JWT
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Procesar request antes de la vista
        if request.user.is_authenticated:
            try:
                # Actualizar último acceso usando queryset (evita serialización del objeto Rol)
                Usuario.objects.filter(pk=request.user.pk).update(
                    fecha_ultimo_acceso=timezone.now()
                )
            except Exception as e:
                logger.error(f"Error actualizando último acceso: {e}")
        
        response = self.get_response(request)
        
        return response


class RequestLoggingMiddleware:
    """
    Middleware para logging de requests de API
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Ignorar requests estáticos
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # Log de request
        if request.user.is_authenticated and request.path.startswith('/api/'):
            logger.info(
                f"API Request: {request.method} {request.path} - "
                f"User: {request.user.email} - IP: {get_client_ip(request)}"
            )
        
        response = self.get_response(request)
        
        return response


class SessionSecurityMiddleware:
    """
    Middleware para validar sesiones activas
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Validar sesión si está autenticado
        if request.user.is_authenticated:
            session_token = request.headers.get('Session-Token')
            
            if session_token:
                # Verificar que la sesión existe y está activa
                sesion_valida = SesionUsuario.objects.filter(
                    usuario=request.user,
                    token_session=session_token,
                    activa=True
                ).exists()
                
                if not sesion_valida:
                    LogAcceso.objects.create(
                        usuario=request.user,
                        tipo_evento='SESSION_INVALID',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        detalles='Intento de uso de sesión inválida',
                        exitoso=False
                    )
                    
                    return JsonResponse({
                        'error': 'Sesión inválida o expirada',
                        'code': 'SESSION_INVALID'
                    }, status=401)
        
        response = self.get_response(request)
        
        return response


class BlockedUserMiddleware:
    """
    Middleware para bloquear usuarios con estado BLOQUEADO
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar si el usuario está bloqueado
            if hasattr(request.user, 'esta_bloqueado') and request.user.esta_bloqueado():
                # Cerrar todas las sesiones
                SesionUsuario.objects.filter(
                    usuario=request.user,
                    activa=True
                ).update(activa=False)
                
                return JsonResponse({
                    'error': 'Usuario bloqueado. Contacte al administrador.',
                    'code': 'USER_BLOCKED'
                }, status=403)
        
        response = self.get_response(request)
        
        return response


class IPWhitelistMiddleware:
    """
    Middleware para restricción por IP (opcional - usar en producción)
    """
    
    # IPs permitidas (configurar según necesidad)
    WHITELIST = [
        '127.0.0.1',
        'localhost',
        # Agregar IPs de oficina/VPN aquí
    ]
    
    # Paths que requieren whitelist (solo endpoints críticos)
    PROTECTED_PATHS = [
        '/admin/',
        '/api/auth/usuarios/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = False  # Activar en producción
    
    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        
        # Verificar si el path está protegido
        path_protected = any(
            request.path.startswith(path) 
            for path in self.PROTECTED_PATHS
        )
        
        if path_protected:
            client_ip = get_client_ip(request)
            
            if client_ip not in self.WHITELIST:
                LogAcceso.objects.create(
                    usuario=request.user if request.user.is_authenticated else None,
                    tipo_evento='IP_BLOCKED',
                    ip_address=client_ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    detalles=f'Intento de acceso desde IP no autorizada: {request.path}',
                    exitoso=False
                )
                
                return JsonResponse({
                    'error': 'Acceso denegado desde esta ubicación',
                    'code': 'IP_NOT_ALLOWED'
                }, status=403)
        
        response = self.get_response(request)
        
        return response


class APIVersionMiddleware:
    """
    Middleware para versionamiento de API
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.current_version = 'v1'
    
    def __call__(self, request):
        # Agregar versión de API a la request
        if request.path.startswith('/api/'):
            api_version = request.headers.get('API-Version', self.current_version)
            request.api_version = api_version
        
        response = self.get_response(request)
        
        # Agregar header de versión a la response
        if request.path.startswith('/api/'):
            response['API-Version'] = self.current_version
        
        return response


class CORSSecurityMiddleware:
    """
    Middleware adicional de CORS (complementa django-cors-headers)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers de seguridad adicionales para CORS
        if request.path.startswith('/api/'):
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class RequestIDMiddleware:
    """
    Middleware para agregar ID único a cada request (útil para debugging)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Generar ID único para la request
        import uuid
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        
        response = self.get_response(request)
        
        # Agregar request ID a la response
        response['X-Request-ID'] = request_id
        
        return response