from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from datetime import timedelta, datetime
from .models import Rol
import uuid
import json

from .models import Usuario, PermisoPersonalizado, SesionUsuario, LogAcceso
from .serializers import (
    CustomTokenObtainPairSerializer, UsuarioSerializer, UsuarioListSerializer,
    CambiarPasswordSerializer, RecuperarPasswordSerializer, RestablecerPasswordSerializer,
    PermisoPersonalizadoSerializer, SesionUsuarioSerializer, LogAccesoSerializer,
    PerfilUsuarioSerializer, RolSerializer
)
from .decorators import (
    jwt_required, admin_required, supervisor_required, role_required,
    module_access_required, rate_limit, get_client_ip, logout_user_sessions
)


# ========================================
# CONFIGURACIÓN DE PAGINACIÓN
# ========================================

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ========================================
# AUTENTICACIÓN Y TOKENS JWT
# ========================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista personalizada para obtener tokens JWT con sesión Django"""
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        # Obtener respuesta original con tokens
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Obtener el usuario autenticado
            from django.contrib.auth import login as django_login
            
            # El serializer ya validó las credenciales y tiene el usuario
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Crear sesión de Django
                user = serializer.user
                django_login(request, user)
                
                # Agregar cookies JWT
                tokens = response.data
                response.set_cookie(
                    key='access_token',
                    value=tokens.get('access'),
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=3600,
                    path='/'
                )
                
                response.set_cookie(
                    key='refresh_token',
                    value=tokens.get('refresh'),
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=86400 * 7,
                    path='/'
                )
        
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """Vista personalizada para refrescar tokens JWT"""
    
    def post(self, request, *args, **kwargs):
        # Buscar refresh token en cookies si no viene en el body
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'error': 'Refresh token requerido'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Agregar el token al request.data si vino de cookies
        if 'refresh' not in request.data:
            # Crear una copia mutable del QueryDict
            mutable_data = request.data.copy()
            mutable_data['refresh'] = refresh_token
            request._full_data = mutable_data
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Actualizar cookie con nuevo access token
            new_access_token = response.data.get('access')
            if new_access_token:
                response.set_cookie(
                    key='access_token',
                    value=new_access_token,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=3600,
                    path='/'
                )
            
            # Actualizar último acceso del usuario
            try:
                token = RefreshToken(refresh_token)
                user_id = token.payload.get('user_id')
                if user_id:
                    Usuario.objects.filter(id=user_id).update(
                        fecha_ultimo_acceso=timezone.now()
                    )
            except Exception:
                pass
        
        return response


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@rate_limit(max_requests=5, window_minutes=15)
def login_view(request):
    """Vista de login con validaciones adicionales"""
    from django.contrib.auth import login as django_login
    serializer = CustomTokenObtainPairSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        tokens = serializer.validated_data
        user = request.user
        
        # Manejar rol como ForeignKey
        user_data = {
            'id': str(user.id),
            'email': user.email,
            'full_name': user.get_full_name(),
            'rol': user.rol.codigo if user.rol else None,
            'rol_nombre': user.rol.nombre if user.rol else None,
            'codigo_empleado': user.codigo_empleado,
        }
        
        # IMPORTANTE: Crear sesión de Django además de JWT
        django_login(request, user)
        
        # Crear respuesta con cookies HttpOnly
        response = Response({
            'message': 'Login exitoso',
            'tokens': tokens,
            'user': user_data
        }, status=status.HTTP_200_OK)
        
        # Establecer cookies HttpOnly para los tokens
        response.set_cookie(
            key='access_token',
            value=tokens['access'],
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=3600,
            path='/'
        )
        
        response.set_cookie(
            key='refresh_token',
            value=tokens['refresh'],
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=86400 * 7,
            path='/'
        )
        
        return response
    
    return Response({
        'error': 'Credenciales inválidas',
        'details': serializer.errors
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@jwt_required
def logout_view(request):
    """Vista de logout que invalida el token"""
    try:
        # Marcar sesión como inactiva
        token_session = request.headers.get('Session-Token')
        if token_session:
            SesionUsuario.objects.filter(
                usuario=request.user,
                token_session=token_session
            ).update(activa=False)
        
        # Registrar logout
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='LOGOUT',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles='Logout manual',
            exitoso=True
        )
        
        # Crear respuesta y eliminar cookies
        response = Response({
            'message': 'Logout exitoso'
        }, status=status.HTTP_200_OK)
        
        # Eliminar cookies de tokens
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/')
        
        return response
        
    except Exception as e:
        return Response({
            'error': 'Error al cerrar sesión',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# GESTIÓN DE PERFIL DE USUARIO
# ========================================

@api_view(['GET'])
@jwt_required
def perfil_usuario_view(request):
    """Obtener perfil del usuario autenticado"""
    serializer = PerfilUsuarioSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@jwt_required
def actualizar_perfil_view(request):
    """Actualizar perfil del usuario autenticado"""
    # Solo permitir actualizar ciertos campos
    allowed_fields = ['nombres', 'apellidos', 'telefono', 'username']
    data = {k: v for k, v in request.data.items() if k in allowed_fields}
    
    serializer = PerfilUsuarioSerializer(request.user, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Perfil actualizado exitosamente',
            'data': serializer.data
        })
    
    return Response({
        'error': 'Error al actualizar perfil',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# GESTIÓN DE CONTRASEÑAS
# ========================================

@api_view(['POST'])
@jwt_required
def cambiar_password_view(request):
    """Cambiar contraseña del usuario autenticado"""
    serializer = CambiarPasswordSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['password_nueva'])
        user.fecha_cambio_password = timezone.now()
        user.save()
        
        # Cerrar todas las sesiones del usuario
        logout_user_sessions(user)
        
        # Registrar cambio de contraseña
        LogAcceso.objects.create(
            usuario=user,
            tipo_evento='PASSWORD_CHANGE',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles='Cambio de contraseña exitoso',
            exitoso=True
        )
        
        return Response({
            'message': 'Contraseña cambiada exitosamente. Debe iniciar sesión nuevamente.'
        })
    
    return Response({
        'error': 'Error al cambiar contraseña',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@rate_limit(max_requests=3, window_minutes=60)
def recuperar_password_view(request):
    """Solicitar recuperación de contraseña"""
    serializer = RecuperarPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = Usuario.objects.get(email=email)
        
        # Generar token de recuperación
        token = str(uuid.uuid4())
        user.token_recuperacion = token
        user.fecha_expiracion_token = timezone.now() + timedelta(hours=24)
        user.save()
        
        # Enviar email (configurar según tus necesidades)
        try:
            send_mail(
                'Recuperación de contraseña - CommerceBox',
                f'Use el siguiente token para restablecer su contraseña: {token}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'Se ha enviado un token de recuperación a su email'
            })
            
        except Exception as e:
            return Response({
                'error': 'Error al enviar email de recuperación',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'error': 'Email inválido',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def restablecer_password_view(request):
    """Restablecer contraseña con token"""
    serializer = RestablecerPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        password_nueva = serializer.validated_data['password_nueva']
        
        user = Usuario.objects.get(token_recuperacion=token)
        user.set_password(password_nueva)
        user.token_recuperacion = ''
        user.fecha_expiracion_token = None
        user.fecha_cambio_password = timezone.now()
        user.save()
        
        # Cerrar todas las sesiones
        logout_user_sessions(user)
        
        return Response({
            'message': 'Contraseña restablecida exitosamente'
        })
    
    return Response({
        'error': 'Token inválido o datos incorrectos',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# GESTIÓN DE USUARIOS (Solo Administradores)
# ========================================

@api_view(['GET'])
@admin_required
def usuarios_list_view(request):
    """Listar todos los usuarios - Solo administradores"""
    search = request.GET.get('search', '')
    rol_id = request.GET.get('rol', '')
    estado = request.GET.get('estado', '')
    
    queryset = Usuario.objects.select_related('rol').all()
    
    if search:
        queryset = queryset.filter(
            Q(nombres__icontains=search) |
            Q(apellidos__icontains=search) |
            Q(email__icontains=search) |
            Q(codigo_empleado__icontains=search)
        )
    
    if rol_id:
        queryset = queryset.filter(rol__id=rol_id)
    
    if estado:
        queryset = queryset.filter(estado=estado)
    
    queryset = queryset.order_by('-date_joined')
    
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = UsuarioListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = UsuarioListSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@admin_required
def usuario_create_view(request):
    """Crear nuevo usuario - Solo administradores"""
    serializer = UsuarioSerializer(data=request.data)
    
    if serializer.is_valid():
        usuario = serializer.save()
        
        # Registrar creación de usuario
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='USER_CREATED',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles=f'Usuario creado: {usuario.get_full_name()} ({usuario.codigo_empleado})',
            exitoso=True
        )
        
        return Response({
            'message': 'Usuario creado exitosamente',
            'data': UsuarioSerializer(usuario).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al crear usuario',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@admin_required
def usuario_detail_view(request, user_id):
    """Obtener detalles de un usuario - Solo administradores"""
    usuario = get_object_or_404(Usuario, id=user_id)
    serializer = UsuarioSerializer(usuario)
    return Response(serializer.data)


@api_view(['PUT'])
@admin_required
def usuario_update_view(request, user_id):
    """Actualizar usuario - Solo administradores"""
    usuario = get_object_or_404(Usuario, id=user_id)
    serializer = UsuarioSerializer(usuario, data=request.data, partial=True)
    
    if serializer.is_valid():
        usuario_updated = serializer.save()
        
        # Registrar actualización
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='USER_UPDATED',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles=f'Usuario actualizado: {usuario_updated.get_full_name()}',
            exitoso=True
        )
        
        return Response({
            'message': 'Usuario actualizado exitosamente',
            'data': serializer.data
        })
    
    return Response({
        'error': 'Error al actualizar usuario',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@admin_required
def usuario_delete_view(request, user_id):
    """Eliminar usuario - Solo administradores"""
    usuario = get_object_or_404(Usuario, id=user_id)
    
    if usuario.id == request.user.id:
        return Response({
            'error': 'No puede eliminar su propia cuenta'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    usuario_info = f"{usuario.get_full_name()} ({usuario.codigo_empleado})"
    usuario.delete()
    
    # Registrar eliminación
    LogAcceso.objects.create(
        usuario=request.user,
        tipo_evento='USER_DELETED',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        detalles=f'Usuario eliminado: {usuario_info}',
        exitoso=True
    )
    
    return Response({
        'message': 'Usuario eliminado exitosamente'
    })


@api_view(['POST'])
@admin_required
def bloquear_usuario_view(request, user_id):
    """Bloquear/desbloquear usuario - Solo administradores"""
    usuario = get_object_or_404(Usuario, id=user_id)
    
    if usuario.id == request.user.id:
        return Response({
            'error': 'No puede bloquear su propia cuenta'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if usuario.estado == 'BLOQUEADO':
        usuario.estado = 'ACTIVO'
        usuario.intentos_fallidos = 0
        usuario.fecha_bloqueo = None
        accion = 'desbloqueado'
    else:
        usuario.estado = 'BLOQUEADO'
        usuario.fecha_bloqueo = timezone.now()
        accion = 'bloqueado'
        
        # Cerrar todas las sesiones del usuario
        logout_user_sessions(usuario)
    
    usuario.save()
    
    # Registrar acción
    LogAcceso.objects.create(
        usuario=request.user,
        tipo_evento='USER_BLOCKED' if accion == 'bloqueado' else 'USER_UNBLOCKED',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        detalles=f'Usuario {accion}: {usuario.get_full_name()}',
        exitoso=True
    )
    
    return Response({
        'message': f'Usuario {accion} exitosamente',
        'estado': usuario.estado
    })


# ========================================
# GESTIÓN DE ROLES Y PERMISOS
# ========================================

@api_view(['GET'])
def roles_disponibles_view(request):
    """Obtener roles disponibles en el sistema"""
    roles = Rol.objects.filter(is_active=True).order_by('nombre')
    serializer = RolSerializer(roles, many=True)
    return Response({'roles': serializer.data})


@api_view(['GET'])
@supervisor_required
def permisos_list_view(request):
    """Listar permisos personalizados"""
    usuario_id = request.GET.get('usuario_id', '')
    modulo = request.GET.get('modulo', '')
    
    queryset = PermisoPersonalizado.objects.select_related('usuario')
    
    if usuario_id:
        queryset = queryset.filter(usuario__id=usuario_id)
    
    if modulo:
        queryset = queryset.filter(modulo=modulo)
    
    queryset = queryset.filter(activo=True).order_by('usuario__apellidos', 'modulo', 'accion')
    
    serializer = PermisoPersonalizadoSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@admin_required
def permiso_create_view(request):
    """Crear permiso personalizado"""
    serializer = PermisoPersonalizadoSerializer(data=request.data)
    
    if serializer.is_valid():
        permiso = serializer.save()
        
        # Registrar creación de permiso
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='PERMISSION_CREATED',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles=f'Permiso creado: {permiso.usuario.get_full_name()} - {permiso.modulo}.{permiso.accion}',
            exitoso=True
        )
        
        return Response({
            'message': 'Permiso creado exitosamente',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al crear permiso',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@admin_required
def permiso_delete_view(request, permiso_id):
    """Eliminar permiso personalizado"""
    try:
        permiso = PermisoPersonalizado.objects.get(id=permiso_id)
        permiso_info = f"{permiso.usuario.get_full_name()} - {permiso.modulo}.{permiso.accion}"
        permiso.delete()
        
        # Registrar eliminación
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='PERMISSION_DELETED',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles=f'Permiso eliminado: {permiso_info}',
            exitoso=True
        )
        
        return Response({
            'message': 'Permiso eliminado exitosamente'
        })
        
    except PermisoPersonalizado.DoesNotExist:
        return Response({
            'error': 'Permiso no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)


# ========================================
# GESTIÓN DE SESIONES
# ========================================

@api_view(['GET'])
@supervisor_required
def sesiones_activas_view(request):
    """Ver sesiones activas - Supervisores y administradores"""
    sesiones = SesionUsuario.objects.filter(activa=True).select_related('usuario')
    serializer = SesionUsuarioSerializer(sesiones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@admin_required
def cerrar_sesion_usuario_view(request, session_id):
    """Cerrar sesión específica - Solo administradores"""
    sesion = get_object_or_404(SesionUsuario, id=session_id)
    sesion.activa = False
    sesion.save()
    
    LogAcceso.objects.create(
        usuario=request.user,
        tipo_evento='SESSION_CLOSED',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        detalles=f'Sesión cerrada forzadamente para: {sesion.usuario.get_full_name()}',
        exitoso=True
    )
    
    return Response({
        'message': 'Sesión cerrada exitosamente'
    })


# ========================================
# LOGS Y AUDITORÍA
# ========================================

@api_view(['GET'])
@supervisor_required
def logs_acceso_view(request):
    """Ver logs de acceso - Supervisores y administradores"""
    usuario_id = request.GET.get('usuario_id', '')
    tipo_evento = request.GET.get('tipo_evento', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    queryset = LogAcceso.objects.select_related('usuario')
    
    if usuario_id:
        queryset = queryset.filter(usuario__id=usuario_id)
    
    if tipo_evento:
        queryset = queryset.filter(tipo_evento=tipo_evento)
    
    if fecha_desde:
        queryset = queryset.filter(fecha_evento__date__gte=fecha_desde)
    
    if fecha_hasta:
        queryset = queryset.filter(fecha_evento__date__lte=fecha_hasta)
    
    queryset = queryset.order_by('-fecha_evento')
    
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = LogAccesoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = LogAccesoSerializer(queryset, many=True)
    return Response(serializer.data)


# ========================================
# REPORTES Y DASHBOARDS
# ========================================

@api_view(['GET'])
@supervisor_required
def reporte_usuarios_activos_view(request):
    """Reporte de usuarios activos"""
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Si no se proporcionan fechas, usar últimos 30 días
    if not fecha_desde or not fecha_hasta:
        fecha_hasta = timezone.now().date()
        fecha_desde = fecha_hasta - timedelta(days=30)
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    
    # Usuarios activos por día
    usuarios_por_dia = []
    current_date = fecha_desde
    
    while current_date <= fecha_hasta:
        usuarios_activos = LogAcceso.objects.filter(
            tipo_evento='LOGIN',
            fecha_evento__date=current_date,
            exitoso=True
        ).values('usuario').distinct().count()
        
        usuarios_por_dia.append({
            'fecha': current_date.strftime('%Y-%m-%d'),
            'usuarios_activos': usuarios_activos
        })
        
        current_date += timedelta(days=1)
    
    # Estadísticas generales
    total_usuarios = Usuario.objects.filter(is_active=True).count()
    usuarios_logueados_periodo = LogAcceso.objects.filter(
        tipo_evento='LOGIN',
        fecha_evento__date__range=[fecha_desde, fecha_hasta],
        exitoso=True
    ).values('usuario').distinct().count()
    
    # Usuarios por rol
    usuarios_por_rol = Usuario.objects.filter(is_active=True).values(
        'rol__nombre', 'rol__codigo'
    ).annotate(
        total=Count('id')
    ).order_by('rol__nombre')
    
    return Response({
        'periodo': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        },
        'resumen': {
            'total_usuarios': total_usuarios,
            'usuarios_logueados_periodo': usuarios_logueados_periodo,
            'porcentaje_actividad': round((usuarios_logueados_periodo / total_usuarios * 100), 2) if total_usuarios > 0 else 0
        },
        'usuarios_por_dia': usuarios_por_dia,
        'usuarios_por_rol': list(usuarios_por_rol)
    })


@api_view(['GET'])
@supervisor_required
def reporte_intentos_fallidos_view(request):
    """Reporte de intentos fallidos"""
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Si no se proporcionan fechas, usar últimos 7 días
    if not fecha_desde or not fecha_hasta:
        fecha_hasta = timezone.now().date()
        fecha_desde = fecha_hasta - timedelta(days=7)
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    
    # Intentos fallidos por día
    intentos_por_dia = []
    current_date = fecha_desde
    
    while current_date <= fecha_hasta:
        intentos_fallidos = LogAcceso.objects.filter(
            tipo_evento='LOGIN_FAILED',
            fecha_evento__date=current_date
        ).count()
        
        intentos_por_dia.append({
            'fecha': current_date.strftime('%Y-%m-%d'),
            'intentos_fallidos': intentos_fallidos
        })
        
        current_date += timedelta(days=1)
    
    # Top IPs con más intentos fallidos
    top_ips = LogAcceso.objects.filter(
        tipo_evento='LOGIN_FAILED',
        fecha_evento__date__range=[fecha_desde, fecha_hasta]
    ).values('ip_address').annotate(
        total_intentos=Count('id')
    ).order_by('-total_intentos')[:10]
    
    # Usuarios con intentos fallidos
    usuarios_intentos = LogAcceso.objects.filter(
        tipo_evento='LOGIN_FAILED',
        fecha_evento__date__range=[fecha_desde, fecha_hasta],
        usuario__isnull=False
    ).values(
        'usuario__id',
        'usuario__email',
        'usuario__nombres',
        'usuario__apellidos'
    ).annotate(
        total_intentos=Count('id')
    ).order_by('-total_intentos')[:10]
    
    # Total de intentos en el período
    total_intentos = LogAcceso.objects.filter(
        tipo_evento='LOGIN_FAILED',
        fecha_evento__date__range=[fecha_desde, fecha_hasta]
    ).count()
    
    return Response({
        'periodo': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        },
        'resumen': {
            'total_intentos_fallidos': total_intentos
        },
        'intentos_por_dia': intentos_por_dia,
        'top_ips': list(top_ips),
        'usuarios_con_intentos': list(usuarios_intentos)
    })


@api_view(['GET'])
@supervisor_required
def reporte_actividad_usuario_view(request, user_id):
    """Reporte detallado de actividad de un usuario específico"""
    try:
        usuario = Usuario.objects.get(id=user_id)
    except Usuario.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Si no se proporcionan fechas, usar últimos 30 días
    if not fecha_desde or not fecha_hasta:
        fecha_hasta = timezone.now().date()
        fecha_desde = fecha_hasta - timedelta(days=30)
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    
    # Actividad por tipo de evento
    actividad_por_tipo = LogAcceso.objects.filter(
        usuario=usuario,
        fecha_evento__date__range=[fecha_desde, fecha_hasta]
    ).values('tipo_evento').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Logins por día
    logins_por_dia = []
    current_date = fecha_desde
    
    while current_date <= fecha_hasta:
        logins = LogAcceso.objects.filter(
            usuario=usuario,
            tipo_evento='LOGIN',
            fecha_evento__date=current_date,
            exitoso=True
        ).count()
        
        logins_por_dia.append({
            'fecha': current_date.strftime('%Y-%m-%d'),
            'logins': logins
        })
        
        current_date += timedelta(days=1)
    
    # IPs utilizadas
    ips_utilizadas = LogAcceso.objects.filter(
        usuario=usuario,
        fecha_evento__date__range=[fecha_desde, fecha_hasta]
    ).values('ip_address').annotate(
        total_accesos=Count('id')
    ).order_by('-total_accesos')
    
    # Último acceso
    ultimo_acceso = LogAcceso.objects.filter(
        usuario=usuario,
        tipo_evento='LOGIN',
        exitoso=True
    ).order_by('-fecha_evento').first()
    
    # Sesiones activas
    sesiones_activas = usuario.sesiones.filter(activa=True).count()
    
    return Response({
        'usuario': {
            'id': str(usuario.id),
            'email': usuario.email,
            'full_name': usuario.get_full_name(),
            'rol': usuario.rol.codigo if usuario.rol else None,
            'rol_nombre': usuario.rol.nombre if usuario.rol else None,
            'estado': usuario.estado,
            'codigo_empleado': usuario.codigo_empleado
        },
        'periodo': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        },
        'resumen': {
            'ultimo_acceso': ultimo_acceso.fecha_evento if ultimo_acceso else None,
            'sesiones_activas': sesiones_activas,
            'intentos_fallidos_actuales': usuario.intentos_fallidos
        },
        'actividad_por_tipo': list(actividad_por_tipo),
        'logins_por_dia': logins_por_dia,
        'ips_utilizadas': list(ips_utilizadas)
    })


@api_view(['GET'])
@admin_required
def dashboard_seguridad_view(request):
    """Dashboard de seguridad - Solo administradores"""
    now = timezone.now()
    hoy = now.date()
    semana_pasada = now - timedelta(days=7)
    
    # Estadísticas generales
    stats = {
        'usuarios_activos': Usuario.objects.filter(is_active=True, estado='ACTIVO').count(),
        'usuarios_bloqueados': Usuario.objects.filter(estado='BLOQUEADO').count(),
        'sesiones_activas': SesionUsuario.objects.filter(activa=True).count(),
        'intentos_fallidos_hoy': LogAcceso.objects.filter(
            tipo_evento='LOGIN_FAILED',
            fecha_evento__date=hoy
        ).count(),
        'logins_exitosos_hoy': LogAcceso.objects.filter(
            tipo_evento='LOGIN',
            fecha_evento__date=hoy
        ).count(),
        'accesos_denegados_semana': LogAcceso.objects.filter(
            tipo_evento='PERMISSION_DENIED',
            fecha_evento__gte=semana_pasada
        ).count(),
    }
    
    # Top IPs con más intentos fallidos
    top_ips_fallidos = LogAcceso.objects.filter(
        tipo_evento='LOGIN_FAILED',
        fecha_evento__gte=semana_pasada
    ).values('ip_address').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Usuarios con más intentos fallidos
    usuarios_intentos_fallidos = Usuario.objects.filter(
        intentos_fallidos__gt=0
    ).order_by('-intentos_fallidos')[:10]
    
    serializer_usuarios = UsuarioListSerializer(usuarios_intentos_fallidos, many=True)
    
    return Response({
        'estadisticas': stats,
        'top_ips_fallidos': list(top_ips_fallidos),
        'usuarios_intentos_fallidos': serializer_usuarios.data
    })


# ========================================
# VERIFICACIÓN Y UTILIDADES
# ========================================

@api_view(['GET'])
@jwt_required
def verificar_token_view(request):
    """Verificar si el token es válido"""
    return Response({
        'valid': True,
        'user': {
            'id': str(request.user.id),
            'email': request.user.email,
            'full_name': request.user.get_full_name(),
            'rol': request.user.rol.codigo if request.user.rol else None,
            'rol_nombre': request.user.rol.nombre if request.user.rol else None,
            'estado': request.user.estado,
        }
    })


@api_view(['GET'])
def health_check_view(request):
    """Health check del sistema de autenticación"""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'auth_system': 'operational'
    })


# ========================================
# GESTIÓN DE ROLES
# ========================================

@api_view(['GET'])
@supervisor_required
def roles_list_api_view(request):
    """Listar todos los roles"""
    search = request.GET.get('search', '')
    is_active = request.GET.get('is_active', '')
    
    queryset = Rol.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search) |
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if is_active:
        queryset = queryset.filter(is_active=(is_active.lower() == 'true'))
    
    queryset = queryset.order_by('-created_at')
    
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = RolSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = RolSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@admin_required
def rol_create_api_view(request):
    """Crear nuevo rol"""
    serializer = RolSerializer(data=request.data)
    
    if serializer.is_valid():
        rol = serializer.save()
        
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='ROL_CREATED',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles=f'Rol creado: {rol.nombre} ({rol.codigo})',
            exitoso=True
        )
        
        return Response({
            'message': 'Rol creado exitosamente',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al crear rol',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@supervisor_required
def rol_detail_api_view(request, rol_id):
    """Obtener detalles de un rol"""
    rol = get_object_or_404(Rol, id=rol_id)
    serializer = RolSerializer(rol)
    return Response(serializer.data)


@api_view(['PUT'])
@admin_required
def rol_update_api_view(request, rol_id):
    """Actualizar rol"""
    rol = get_object_or_404(Rol, id=rol_id)
    serializer = RolSerializer(rol, data=request.data, partial=True)
    
    if serializer.is_valid():
        rol_updated = serializer.save()
        
        LogAcceso.objects.create(
            usuario=request.user,
            tipo_evento='ROL_UPDATED',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles=f'Rol actualizado: {rol_updated.nombre}',
            exitoso=True
        )
        
        return Response({
            'message': 'Rol actualizado exitosamente',
            'data': serializer.data
        })
    
    return Response({
        'error': 'Error al actualizar rol',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@admin_required
def rol_delete_api_view(request, rol_id):
    """Eliminar rol"""
    rol = get_object_or_404(Rol, id=rol_id)
    
    # Verificar que no haya usuarios con este rol
    usuarios_con_rol = Usuario.objects.filter(rol=rol).count()
    if usuarios_con_rol > 0:
        return Response({
            'error': f'No se puede eliminar el rol porque tiene {usuarios_con_rol} usuario(s) asignado(s)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    rol_info = f"{rol.nombre} ({rol.codigo})"
    rol.delete()
    
    LogAcceso.objects.create(
        usuario=request.user,
        tipo_evento='ROL_DELETED',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        detalles=f'Rol eliminado: {rol_info}',
        exitoso=True
    )
    
    return Response({
        'message': 'Rol eliminado exitosamente'
    })