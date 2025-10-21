from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import jwt
from django.conf import settings

Usuario = get_user_model()

class DualAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware que maneja autenticación dual: JWT + Django Sessions
    Prioridad: Sessions > JWT > Anonymous
    """
    
    def process_request(self, request):
        # 1. Si ya está autenticado por SessionMiddleware, no hacer nada
        if hasattr(request, 'user') and request.user.is_authenticated:
            return None
        
        # 2. Intentar autenticar con JWT desde cookies
        token = request.COOKIES.get('access_token')
        
        if token:
            try:
                # Decodificar el token JWT
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=['HS256']
                )
                
                user_id = payload.get('user_id')
                
                if user_id:
                    try:
                        user = Usuario.objects.get(id=user_id)
                        request.user = user
                        return None
                    except Usuario.DoesNotExist:
                        pass
                        
            except (jwt.ExpiredSignatureError, jwt.DecodeError, ValueError):
                pass
        

        # 3. Si todo falla, dejar como AnonymousUser (ya establecido por Django)
        return None

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
class JWTAuthFromCookieMiddleware:
    """
    Middleware que extrae el JWT token desde cookies HTTP-only
    y lo coloca en el header Authorization para que Django REST Framework
    lo pueda procesar correctamente.
    
    Esto soluciona el problema donde JWTAuthentication no lee automáticamente
    desde las cookies HTTP-only que se configuran en el login.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Leer el access_token desde las cookies
        access_token = request.COOKIES.get('access_token')
        
        # Si existe el token Y no hay un header Authorization previo, agregarlo
        if access_token and not request.META.get('HTTP_AUTHORIZATION'):
            # Agregar el token al header en el formato esperado por JWT
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        
        response = self.get_response(request)
        return response

