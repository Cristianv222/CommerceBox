# apps/financial_management/mixins.py

"""
Mixins de permisos y control de acceso para el módulo financiero
Incluye control para: Cajas, Caja Chica, Créditos (CxC y CxP)
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy


# ============================================================================
# MIXIN BASE - ACCESO GENERAL AL MÓDULO FINANCIERO
# ============================================================================

class FinancialAccessMixin(LoginRequiredMixin):
    """
    Mixin base para acceso al módulo financiero
    Usuarios con rol: ADMIN, SUPERVISOR, CAJERO, CONTADOR, GERENTE
    """
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
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'CAJERO', 'GERENTE', 'CONTADOR']
            if request.user.rol in allowed_roles:
                return super().dispatch(request, *args, **kwargs)
        
        # Por defecto, permitir acceso si está autenticado
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# MIXINS PARA GESTIÓN DE CAJAS
# ============================================================================

class CajaEditMixin(FinancialAccessMixin):
    """
    Mixin para vistas que requieren permisos de edición de caja
    Solo ADMIN, SUPERVISOR, GERENTE
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Si es superuser o staff, permitir
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar permiso específico si el método existe
        if hasattr(request.user, 'tiene_permiso'):
            if not request.user.tiene_permiso('financial.change_caja'):
                messages.error(request, "No tienes permisos para gestionar cajas.")
                return redirect('financial_management:dashboard')
        elif hasattr(request.user, 'rol'):
            # Verificar rol
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'GERENTE']
            if request.user.rol not in allowed_roles:
                messages.error(request, "No tienes permisos para gestionar cajas.")
                return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class CajeroAccessMixin(FinancialAccessMixin):
    """
    Mixin para operaciones de cajero
    ADMIN, SUPERVISOR, CAJERO, GERENTE
    """
    
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
    """
    Mixin para acciones que requieren supervisor o admin
    ADMIN, SUPERVISOR, GERENTE
    """
    
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


# ============================================================================
# MIXINS PARA CAJA CHICA
# ============================================================================

class CajaChicaAccessMixin(FinancialAccessMixin):
    """
    Mixin para acceso a caja chica
    ADMIN, SUPERVISOR, GERENTE, o RESPONSABLE de la caja chica
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Permitir a staff y superuser
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar rol si existe
        if hasattr(request.user, 'rol'):
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'GERENTE']
            if request.user.rol in allowed_roles:
                return super().dispatch(request, *args, **kwargs)
            
            # Si no es admin/supervisor/gerente, debe ser responsable de alguna caja chica
            # Esta validación adicional se hace en la vista específica
        
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# MIXINS PARA GESTIÓN DE CRÉDITOS (CxC y CxP)
# ============================================================================

class CreditoAccessMixin(FinancialAccessMixin):
    """
    Mixin para gestión de créditos (cuentas por cobrar y pagar)
    ADMIN, SUPERVISOR, CONTADOR, GERENTE
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Si es superuser o staff, permitir
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar rol si existe
        if hasattr(request.user, 'rol'):
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'CONTADOR', 'GERENTE']
            if request.user.rol not in allowed_roles:
                messages.error(request, "No tienes permiso para gestionar créditos.")
                return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class ContadorAccessMixin(FinancialAccessMixin):
    """
    Mixin para operaciones contables
    Solo ADMIN, SUPERVISOR, CONTADOR, GERENTE
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Si es superuser o staff, permitir
        if request.user.is_superuser or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar rol si existe
        if hasattr(request.user, 'rol'):
            allowed_roles = ['ADMIN', 'SUPERVISOR', 'CONTADOR', 'GERENTE']
            if request.user.rol not in allowed_roles:
                messages.error(request, "Solo personal contable puede acceder a esta sección.")
                return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# MIXIN PARA MENSAJES AUTOMÁTICOS EN FORMULARIOS
# ============================================================================

class FormMessagesMixin:
    """
    Mixin para agregar mensajes de éxito/error automáticamente en formularios
    """
    success_message = "Operación realizada exitosamente."
    error_message = "Por favor corrige los errores en el formulario."
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            # Formatear mensaje con objeto si existe
            if hasattr(self, 'object'):
                msg = self.success_message.format(object=self.object)
            else:
                msg = self.success_message
            messages.success(self.request, msg)
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, self.error_message)
        return super().form_invalid(form)


# ============================================================================
# MIXINS ADICIONALES DE UTILIDAD
# ============================================================================

class AjaxResponseMixin:
    """
    Mixin para respuestas AJAX
    Útil para APIs internas del módulo
    """
    
    def render_to_json_response(self, context, **response_kwargs):
        """Renderizar respuesta como JSON"""
        from django.http import JsonResponse
        return JsonResponse(context, **response_kwargs)
    
    def form_invalid_ajax(self, form):
        """Respuesta JSON para formulario inválido"""
        return self.render_to_json_response({
            'success': False,
            'errors': form.errors
        }, status=400)
    
    def form_valid_ajax(self, form):
        """Respuesta JSON para formulario válido"""
        return self.render_to_json_response({
            'success': True,
            'message': 'Operación exitosa'
        })