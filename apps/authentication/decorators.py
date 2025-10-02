from functools import wraps
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import LogAcceso, SesionUsuario
import jwt
from django.conf import settings

Usuario = get_user_model()


class CustomJWTAuthentication(JWTAuthentication):
    """Autenticación JWT personalizada con validaciones adicionales"""
    
    def authenticate(self, request):
        # PASO 1: Buscar token en COOKIES primero (navegación HTML normal)
        raw_token = request.COOKIES.get('access_token')
        
        # PASO 2: Si no está en cookies, buscar en HEADER (peticiones API con Authorization)
        if not raw_token:
            header = self.get_header(request)
            if header is None:
                return None
            
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
        
        # Si después de buscar en ambos lugares no hay token, retornar None
        if raw_token is None:
            return None
        
        # Validar el token JWT
        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            return None
        
        # Obtener el usuario del token
        user = self.get_user(validated_token)
        
        # Validaciones adicionales de negocio
        if not user.is_active or user.estado != 'ACTIVO':
            raise AuthenticationFailed('Usuario inactivo')
        
        if user.esta_bloqueado():
            raise AuthenticationFailed('Usuario bloqueado')
        
        # Actualizar último acceso
        user.fecha_ultimo_acceso = timezone.now()
        user.save(update_fields=['fecha_ultimo_acceso'])
        
        return user, validated_token


def jwt_required(view_func):
    """Decorador que requiere autenticación JWT válida"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        auth = CustomJWTAuthentication()
        try:
            result = auth.authenticate(request)
            if result is None:
                return JsonResponse({
                    'error': 'Token de autenticación requerido',
                    'code': 'TOKEN_REQUIRED'
                }, status=401)
            
            user, token = result
            request.user = user
            request.token = token
            return view_func(request, *args, **kwargs)
            
        except (InvalidToken, TokenError) as e:
            return JsonResponse({
                'error': 'Token inválido',
                'code': 'INVALID_TOKEN',
                'details': str(e)
            }, status=401)
        except AuthenticationFailed as e:
            return JsonResponse({
                'error': str(e),
                'code': 'AUTHENTICATION_FAILED'
            }, status=401)
        except Exception as e:
            return JsonResponse({
                'error': 'Error de autenticación',
                'code': 'AUTH_ERROR',
                'details': str(e)
            }, status=500)
    
    return wrapped_view


def role_required(*roles):
    """Decorador que requiere uno o más roles específicos"""
    def decorator(view_func):
        @wraps(view_func)
        @jwt_required
        def wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if not any(user.rol == role for role in roles):
                # Registrar intento de acceso no autorizado
                LogAcceso.objects.create(
                    usuario=user,
                    tipo_evento='PERMISSION_DENIED',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    detalles=f'Intento de acceso con rol {user.rol} a endpoint que requiere {roles}',
                    exitoso=False
                )
                
                return JsonResponse({
                    'error': 'No tiene permisos para acceder a este recurso',
                    'code': 'INSUFFICIENT_PERMISSIONS',
                    'required_roles': roles,
                    'user_role': user.rol
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def admin_required(view_func):
    """Decorador que requiere rol de administrador"""
    return role_required('ADMIN')(view_func)


def supervisor_required(view_func):
    """Decorador que requiere rol de supervisor o superior"""
    return role_required('ADMIN', 'SUPERVISOR')(view_func)


def vendedor_required(view_func):
    """Decorador que requiere permisos de venta"""
    @wraps(view_func)
    @jwt_required
    def wrapped_view(request, *args, **kwargs):
        user = request.user
        
        if not user.is_vendedor():
            LogAcceso.objects.create(
                usuario=user,
                tipo_evento='PERMISSION_DENIED',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                detalles=f'Intento de acceso a funcionalidad de ventas con rol {user.rol}',
                exitoso=False
            )
            
            return JsonResponse({
                'error': 'No tiene permisos para realizar ventas',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapped_view


def cajero_required(view_func):
    """Decorador que requiere permisos de caja"""
    @wraps(view_func)
    @jwt_required
    def wrapped_view(request, *args, **kwargs):
        user = request.user
        
        if not user.is_cajero():
            LogAcceso.objects.create(
                usuario=user,
                tipo_evento='PERMISSION_DENIED',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                detalles=f'Intento de acceso a funcionalidad de caja con rol {user.rol}',
                exitoso=False
            )
            
            return JsonResponse({
                'error': 'No tiene permisos para manejar caja',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapped_view


def module_access_required(module_name):
    """Decorador que requiere acceso a un módulo específico"""
    def decorator(view_func):
        @wraps(view_func)
        @jwt_required
        def wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if not user.puede_acceder_modulo(module_name):
                LogAcceso.objects.create(
                    usuario=user,
                    tipo_evento='PERMISSION_DENIED',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    detalles=f'Intento de acceso al módulo {module_name} con rol {user.rol}',
                    exitoso=False
                )
                
                return JsonResponse({
                    'error': f'No tiene permisos para acceder al módulo {module_name}',
                    'code': 'MODULE_ACCESS_DENIED',
                    'module': module_name
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def custom_permission_required(module, action):
    """Decorador que requiere un permiso personalizado específico"""
    def decorator(view_func):
        @wraps(view_func)
        @jwt_required
        def wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Verificar permisos base por rol
            if not user.puede_acceder_modulo(module):
                return JsonResponse({
                    'error': f'No tiene acceso al módulo {module}',
                    'code': 'MODULE_ACCESS_DENIED'
                }, status=403)
            
            # Verificar permisos personalizados
            has_permission = user.permisos_personalizados.filter(
                modulo=module,
                accion=action,
                activo=True
            ).exists()
            
            if not has_permission and not user.is_admin():
                LogAcceso.objects.create(
                    usuario=user,
                    tipo_evento='PERMISSION_DENIED',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    detalles=f'Intento de acción {action} en módulo {module} sin permisos',
                    exitoso=False
                )
                
                return JsonResponse({
                    'error': f'No tiene permisos para la acción {action} en {module}',
                    'code': 'ACTION_NOT_PERMITTED',
                    'module': module,
                    'action': action
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def rate_limit(max_requests=60, window_minutes=1):
    """Decorador para limitar la cantidad de requests por usuario"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Para endpoints sin autenticación (como login), usar IP
            user = getattr(request, 'user', None)
            ip_address = get_client_ip(request)
            now = timezone.now()
            window_start = now - timezone.timedelta(minutes=window_minutes)
            
            # Contar requests en la ventana de tiempo
            if user and hasattr(user, 'id'):
                recent_requests = LogAcceso.objects.filter(
                    usuario=user,
                    fecha_evento__gte=window_start,
                    tipo_evento='API_REQUEST'
                ).count()
            else:
                # Si no hay usuario autenticado, contar por IP
                recent_requests = LogAcceso.objects.filter(
                    ip_address=ip_address,
                    fecha_evento__gte=window_start,
                    tipo_evento='API_REQUEST'
                ).count()
            
            if recent_requests >= max_requests:
                return JsonResponse({
                    'error': 'Demasiadas solicitudes. Intente más tarde.',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'max_requests': max_requests,
                    'window_minutes': window_minutes
                }, status=429)
            
            # Registrar la request
            LogAcceso.objects.create(
                usuario=user if user and hasattr(user, 'id') else None,
                tipo_evento='API_REQUEST',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                detalles=f'{request.method} {request.path}',
                exitoso=True
            )
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def get_client_ip(request):
    """Obtener la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class SecurityMiddleware:
    """Middleware de seguridad personalizado"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Procesar request
        response = self.get_response(request)
        
        # Agregar headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


def logout_user_sessions(user):
    """Cerrar todas las sesiones activas de un usuario"""
    SesionUsuario.objects.filter(usuario=user, activa=True).update(activa=False)
    
    # Registrar logout forzado
    LogAcceso.objects.create(
        usuario=user,
        tipo_evento='LOGOUT',
        ip_address='127.0.0.1',  # Sistema
        user_agent='Sistema',
        detalles='Logout forzado de todas las sesiones',
        exitoso=True
    )


def validate_session_token(user, session_token):
    """Validar que el token de sesión sea válido"""
    return SesionUsuario.objects.filter(
        usuario=user,
        token_session=session_token,
        activa=True
    ).exists()