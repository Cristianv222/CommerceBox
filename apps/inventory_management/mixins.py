# apps/inventory_management/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy


class InventarioAccessMixin(LoginRequiredMixin):
    """Mixin para verificar acceso al módulo de inventario"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.puede_acceder_modulo('inventory'):
            messages.error(request, "No tienes permisos para acceder al inventario.")
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class InventarioEditMixin(InventarioAccessMixin):
    """Mixin para vistas que requieren permisos de edición"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.tiene_permiso('inventory.change_producto'):
            messages.error(request, "No tienes permisos para editar el inventario.")
            return redirect('inventory_management:dashboard')
        return super().dispatch(request, *args, **kwargs)


class InventarioDeleteMixin(InventarioAccessMixin):
    """Mixin para vistas que requieren permisos de eliminación"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.tiene_permiso('inventory.delete_producto'):
            messages.error(request, "No tienes permisos para eliminar del inventario.")
            return redirect('inventory_management:dashboard')
        return super().dispatch(request, *args, **kwargs)


class AjaxInventarioMixin(InventarioAccessMixin):
    """Mixin para vistas AJAX de inventario"""
    
    def handle_no_permission(self):
        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos para realizar esta acción.'
        }, status=403)


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
        return response


class DeleteMessageMixin:
    """Mixin para agregar un mensaje de éxito al eliminar un objeto"""
    delete_message = "El elemento ha sido eliminado exitosamente."
    
    def delete(self, request, *args, **kwargs):
        # Obtener el objeto antes de eliminarlo para usarlo en el mensaje
        obj = self.get_object()
        
        # Formatear el mensaje con el objeto si está disponible
        if hasattr(self, 'delete_message') and self.delete_message:
            message = self.delete_message.format(object=obj)
            messages.success(self.request, message)
        
        # Llamar al método delete del padre
        return super().delete(request, *args, **kwargs)