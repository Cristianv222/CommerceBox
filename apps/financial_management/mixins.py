# apps/financial_management/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy


class FinancialAccessMixin(LoginRequiredMixin):
    """Mixin para verificar acceso al módulo financiero"""
    login_url = '/login/'
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar que el usuario esté autenticado
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar acceso al módulo si el método existe
        if hasattr(request.user, 'puede_acceder_modulo'):
            if not request.user.puede_acceder_modulo('financial'):
                messages.error(request, "No tienes permisos para acceder al módulo financiero.")
                return redirect('custom_admin:dashboard')
        
        # Si es staff o superuser, permitir acceso
        if request.user.is_staff or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Si tiene rol definido, verificar
        if hasattr(request.user, 'rol'):
            # Permitir acceso a roles específicos
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'CAJERO', 'GERENTE']
            if request.user.rol in allowed_roles:
                return super().dispatch(request, *args, **kwargs)
        
        # Por defecto, permitir acceso si está autenticado
        return super().dispatch(request, *args, **kwargs)


class CajaEditMixin(FinancialAccessMixin):
    """Mixin para vistas que requieren permisos de edición de caja"""
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar permiso específico si el método existe
        if hasattr(request.user, 'tiene_permiso'):
            if not request.user.tiene_permiso('financial.change_caja'):
                messages.error(request, "No tienes permisos para gestionar cajas.")
                return redirect('financial_management:dashboard')
        elif not (request.user.is_staff or request.user.is_superuser):
            # Si no tiene el método, verificar que sea staff o superuser
            messages.error(request, "No tienes permisos para gestionar cajas.")
            return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class CajeroAccessMixin(FinancialAccessMixin):
    """Mixin para operaciones de cajero"""
    
    def dispatch(self, request, *args, **kwargs):
        # Si es superuser o staff, permitir
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar rol si existe
        if hasattr(request.user, 'rol'):
            allowed_roles = ['CAJERO', 'SUPERVISOR', 'ADMIN', 'GERENTE']
            if request.user.rol not in allowed_roles:
                messages.error(request, "Solo cajeros pueden realizar esta acción.")
                return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class SupervisorAccessMixin(FinancialAccessMixin):
    """Mixin para acciones que requieren supervisor o admin"""
    
    def dispatch(self, request, *args, **kwargs):
        # Si es superuser o staff, permitir
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar rol si existe
        if hasattr(request.user, 'rol'):
            allowed_roles = ['SUPERVISOR', 'ADMIN', 'GERENTE']
            if request.user.rol not in allowed_roles:
                messages.error(request, "Se requiere autorización de supervisor.")
                return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class CajaChicaAccessMixin(FinancialAccessMixin):
    """Mixin para acceso a caja chica"""
    
    def dispatch(self, request, *args, **kwargs):
        # Permitir a staff y superuser
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar rol si existe
        if hasattr(request.user, 'rol'):
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'GERENTE']
            if request.user.rol not in allowed_roles:
                messages.error(request, "No tienes permisos para gestionar caja chica.")
                return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class FormMessagesMixin:
    """Mixin para agregar mensajes de éxito automáticamente en formularios"""
    success_message = "Operación realizada exitosamente."
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, "Por favor corrige los errores en el formulario.")
        return super().form_invalid(form)
