"""
CommerceBox - URLs del módulo de autenticación
Incluye endpoints JWT, gestión de usuarios, permisos y auditoría
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView

from . import views

app_name = 'authentication'

urlpatterns = [
    # ========================================
    # AUTENTICACIÓN JWT
    # ========================================
    
    # Obtener tokens (login)
    path('login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # Refrescar token
    path('login/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # Logout (invalidar token)
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    
    # Verificar token
    path('verify/', views.verificar_token_view, name='token_verify'),
    
    # ========================================
    # GESTIÓN DE PERFIL
    # ========================================
    
    # Ver perfil propio
    path('perfil/', views.perfil_usuario_view, name='perfil'),
    
    # Actualizar perfil propio
    path('perfil/actualizar/', views.actualizar_perfil_view, name='actualizar_perfil'),
    
    # ========================================
    # GESTIÓN DE CONTRASEÑAS
    # ========================================
    
    # Cambiar contraseña (usuario autenticado)
    path('password/cambiar/', views.cambiar_password_view, name='cambiar_password'),
    
    # Recuperar contraseña (solicitar token)
    path('password/recuperar/', views.recuperar_password_view, name='recuperar_password'),
    
    # Restablecer contraseña (con token)
    path('password/restablecer/', views.restablecer_password_view, name='restablecer_password'),
    
    # ========================================
    # GESTIÓN DE USUARIOS (Admin)
    # ========================================
    
    # Listar usuarios
    path('usuarios/', views.usuarios_list_view, name='usuarios_list'),
    
    # Crear usuario
    path('usuarios/crear/', views.usuario_create_view, name='usuario_create'),
    
    # Detalle de usuario
    path('usuarios/<uuid:user_id>/', views.usuario_detail_view, name='usuario_detail'),
    
    # Actualizar usuario
    path('usuarios/<uuid:user_id>/actualizar/', views.usuario_update_view, name='usuario_update'),
    
    # Eliminar usuario
    path('usuarios/<uuid:user_id>/eliminar/', views.usuario_delete_view, name='usuario_delete'),
    
    # Bloquear/Desbloquear usuario
    path('usuarios/<uuid:user_id>/bloquear/', views.bloquear_usuario_view, name='bloquear_usuario'),
    
    # ========================================
    # ROLES Y PERMISOS
    # ========================================
    
    # Roles disponibles
    path('roles/', views.roles_disponibles_view, name='roles_disponibles'),
    
    # Listar permisos personalizados
    path('permisos/', views.permisos_list_view, name='permisos_list'),
    
    # Crear permiso personalizado
    path('permisos/crear/', views.permiso_create_view, name='permiso_create'),
    
    # Eliminar permiso personalizado
    path('permisos/<int:permiso_id>/eliminar/', views.permiso_delete_view, name='permiso_delete'),
    
    # ========================================
    # GESTIÓN DE SESIONES
    # ========================================
    
    # Ver sesiones activas
    path('sesiones/activas/', views.sesiones_activas_view, name='sesiones_activas'),
    
    # Cerrar sesión específica
    path('sesiones/<int:session_id>/cerrar/', views.cerrar_sesion_usuario_view, name='cerrar_sesion'),
    
    # ========================================
    # LOGS Y AUDITORÍA
    # ========================================
    
    # Ver logs de acceso
    path('logs/', views.logs_acceso_view, name='logs_acceso'),
    
    # ========================================
    # REPORTES Y DASHBOARDS
    # ========================================
    
    # Reporte de usuarios activos
    path('reportes/usuarios-activos/', views.reporte_usuarios_activos_view, name='reporte_usuarios_activos'),
    
    # Reporte de intentos fallidos
    path('reportes/intentos-fallidos/', views.reporte_intentos_fallidos_view, name='reporte_intentos_fallidos'),
    
    # Reporte de actividad de usuario específico
    path('reportes/actividad-usuario/<uuid:user_id>/', views.reporte_actividad_usuario_view, name='reporte_actividad_usuario'),
    
    # Dashboard de seguridad
    path('dashboard/seguridad/', views.dashboard_seguridad_view, name='dashboard_seguridad'),
    
    # ========================================
    # UTILIDADES
    # ========================================
    
    # Health check
    path('health/', views.health_check_view, name='health_check'),
]