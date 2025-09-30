"""
Permission classes personalizadas para Django REST Framework
"""
from rest_framework import permissions
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class IsAdmin(permissions.BasePermission):
    """
    Permiso que solo permite acceso a administradores
    """
    message = 'Solo los administradores pueden realizar esta acción.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_admin') and
            request.user.is_admin()
        )


class IsSupervisor(permissions.BasePermission):
    """
    Permiso que permite acceso a supervisores y administradores
    """
    message = 'Solo los supervisores y administradores pueden realizar esta acción.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_supervisor') and
            request.user.is_supervisor()
        )


class IsVendedor(permissions.BasePermission):
    """
    Permiso que permite acceso a vendedores y superiores
    """
    message = 'Necesita permisos de vendedor para realizar esta acción.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_vendedor') and
            request.user.is_vendedor()
        )


class IsCajero(permissions.BasePermission):
    """
    Permiso que permite acceso a cajeros y superiores
    """
    message = 'Necesita permisos de cajero para realizar esta acción.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_cajero') and
            request.user.is_cajero()
        )


class HasModuleAccess(permissions.BasePermission):
    """
    Permiso que verifica acceso a un módulo específico
    Se debe especificar el módulo en la vista
    """
    message = 'No tiene permisos para acceder a este módulo.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Obtener módulo de la vista
        module = getattr(view, 'required_module', None)
        
        if not module:
            return True  # Si no se especifica módulo, permitir acceso
        
        return (
            hasattr(request.user, 'puede_acceder_modulo') and
            request.user.puede_acceder_modulo(module)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso que solo permite al dueño del objeto o a un admin
    """
    message = 'Solo puede modificar sus propios datos o ser administrador.'
    
    def has_object_permission(self, request, view, obj):
        # Admins pueden todo
        if hasattr(request.user, 'is_admin') and request.user.is_admin():
            return True
        
        # El objeto debe tener un campo 'usuario' o ser el usuario mismo
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
        
        return obj == request.user


class IsActiveUser(permissions.BasePermission):
    """
    Permiso que solo permite acceso a usuarios activos
    """
    message = 'Su cuenta no está activa. Contacte al administrador.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar estado activo
        if hasattr(request.user, 'estado'):
            return request.user.estado == 'ACTIVO'
        
        return request.user.is_active


class ReadOnly(permissions.BasePermission):
    """
    Permiso de solo lectura
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite lectura a todos, pero escritura solo a admins
    """
    def has_permission(self, request, view):
        # Permitir lectura a todos los autenticados
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Escritura solo para admins
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_admin') and
            request.user.is_admin()
        )


class HasCustomPermission(permissions.BasePermission):
    """
    Permiso que verifica permisos personalizados del usuario
    """
    message = 'No tiene el permiso requerido para esta acción.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Obtener módulo y acción de la vista
        module = getattr(view, 'required_module', None)
        action = getattr(view, 'required_action', None)
        
        if not module or not action:
            return True
        
        # Admins siempre tienen acceso
        if hasattr(request.user, 'is_admin') and request.user.is_admin():
            return True
        
        # Verificar permiso personalizado
        from .models import PermisoPersonalizado
        from django.utils import timezone
        
        return PermisoPersonalizado.objects.filter(
            usuario=request.user,
            modulo=module,
            accion=action,
            activo=True,
            fecha_expiracion__gt=timezone.now()
        ).exists() or PermisoPersonalizado.objects.filter(
            usuario=request.user,
            modulo=module,
            accion=action,
            activo=True,
            fecha_expiracion__isnull=True
        ).exists()


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Permiso que permite al usuario ver/modificar solo su propia información
    o ser administrador
    """
    message = 'Solo puede acceder a su propia información.'
    
    def has_object_permission(self, request, view, obj):
        # Admins pueden ver todo
        if hasattr(request.user, 'is_admin') and request.user.is_admin():
            return True
        
        # Usuario solo puede ver/modificar su propia info
        return obj == request.user


class CanCreateUser(permissions.BasePermission):
    """
    Permiso para crear usuarios
    """
    message = 'No tiene permisos para crear usuarios.'
    
    def has_permission(self, request, view):
        # Solo admins pueden crear usuarios
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_admin') and
            request.user.is_admin()
        )


class CanDeleteUser(permissions.BasePermission):
    """
    Permiso para eliminar usuarios
    """
    message = 'No tiene permisos para eliminar usuarios.'
    
    def has_permission(self, request, view):
        # Solo admins pueden eliminar usuarios
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_admin') and
            request.user.is_admin()
        )
    
    def has_object_permission(self, request, view, obj):
        # No puede eliminarse a sí mismo
        if obj == request.user:
            self.message = 'No puede eliminar su propia cuenta.'
            return False
        
        return True


class CanViewLogs(permissions.BasePermission):
    """
    Permiso para ver logs de auditoría
    """
    message = 'No tiene permisos para ver logs de auditoría.'
    
    def has_permission(self, request, view):
        # Supervisores y admins pueden ver logs
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_supervisor') and
            request.user.is_supervisor()
        )


class CanManageSessions(permissions.BasePermission):
    """
    Permiso para gestionar sesiones
    """
    message = 'No tiene permisos para gestionar sesiones.'
    
    def has_permission(self, request, view):
        # Solo admins pueden gestionar sesiones
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'is_admin') and
            request.user.is_admin()
        )


class IsNotBlocked(permissions.BasePermission):
    """
    Permiso que verifica que el usuario no esté bloqueado
    """
    message = 'Su cuenta está bloqueada. Contacte al administrador.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'esta_bloqueado'):
            return not request.user.esta_bloqueado()
        
        return True


# Composición de permisos comunes
class AdminPermissions(permissions.BasePermission):
    """
    Permiso compuesto: Admin + Activo + No bloqueado
    """
    def has_permission(self, request, view):
        checks = [
            IsAdmin(),
            IsActiveUser(),
            IsNotBlocked()
        ]
        
        return all(check.has_permission(request, view) for check in checks)


class SupervisorPermissions(permissions.BasePermission):
    """
    Permiso compuesto: Supervisor + Activo + No bloqueado
    """
    def has_permission(self, request, view):
        checks = [
            IsSupervisor(),
            IsActiveUser(),
            IsNotBlocked()
        ]
        
        return all(check.has_permission(request, view) for check in checks)