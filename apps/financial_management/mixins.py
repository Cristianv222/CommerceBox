# apps/financial_management/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy


class FinancialAccessMixin(LoginRequiredMixin):
    """Mixin para verificar acceso al módulo financiero"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.puede_acceder_modulo('financial'):
            messages.error(request, "No tienes permisos para acceder al módulo financiero.")
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class CajaEditMixin(FinancialAccessMixin):
    """Mixin para vistas que requieren permisos de edición de caja"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.tiene_permiso('financial.change_caja'):
            messages.error(request, "No tienes permisos para gestionar cajas.")
            return redirect('financial_management:dashboard')
        return super().dispatch(request, *args, **kwargs)


class CajeroAccessMixin(FinancialAccessMixin):
    """Mixin para operaciones de cajero (abrir/cerrar caja, registrar movimientos)"""
    
    def dispatch(self, request, *args, **kwargs):
        # Cajeros, supervisores y admins pueden operar caja
        if request.user.rol not in ['CAJERO', 'SUPERVISOR', 'ADMIN']:
            messages.error(request, "Solo cajeros pueden realizar esta acción.")
            return redirect('financial_management:dashboard')
        return super().dispatch(request, *args, **kwargs)


class SupervisorAccessMixin(FinancialAccessMixin):
    """Mixin para acciones que requieren supervisor o admin"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.rol not in ['SUPERVISOR', 'ADMIN']:
            messages.error(request, "Se requiere autorización de supervisor.")
            return redirect('financial_management:dashboard')
        return super().dispatch(request, *args, **kwargs)


class CajaChicaAccessMixin(FinancialAccessMixin):
    """Mixin para acceso a caja chica"""
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar si es responsable de alguna caja chica o tiene permisos especiales
        from .models import CajaChica
        
        es_responsable = CajaChica.objects.filter(
            responsable=request.user,
            estado='ACTIVA'
        ).exists()
        
        es_autorizado = request.user.rol in ['ADMIN', 'SUPERVISOR']
        
        if not (es_responsable or es_autorizado):
            messages.error(request, "No tienes acceso a caja chica.")
            return redirect('financial_management:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class FormMessagesMixin:
    """Mixin para agregar mensajes automáticos en formularios"""
    success_message = None
    error_message = None
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message.format(object=self.object))
        return response
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.error_message:
            messages.error(self.request, self.error_message)
        else:
            messages.error(
                self.request,
                "Por favor corrija los errores en el formulario."
            )
        return response