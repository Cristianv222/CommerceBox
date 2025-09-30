# apps/inventory_management/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


def inventario_access_required(view_func):
    """
    Decorador para verificar acceso al módulo de inventario
    Útil para vistas basadas en funciones
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.puede_acceder_modulo('inventory'):
            messages.error(request, "No tienes permisos para acceder al inventario.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def ajax_inventario_access_required(view_func):
    """
    Decorador para vistas AJAX que requieren acceso a inventario
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.puede_acceder_modulo('inventory'):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para acceder al inventario.'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def puede_editar_inventario(view_func):
    """
    Decorador para verificar permisos de edición
    """
    @wraps(view_func)
    @inventario_access_required
    def wrapper(request, *args, **kwargs):
        if not request.user.tiene_permiso('inventory.change_producto'):
            messages.error(request, "No tienes permisos para editar el inventario.")
            return redirect('inventory_management:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def puede_eliminar_inventario(view_func):
    """
    Decorador para verificar permisos de eliminación
    """
    @wraps(view_func)
    @inventario_access_required
    def wrapper(request, *args, **kwargs):
        if not request.user.tiene_permiso('inventory.delete_producto'):
            messages.error(request, "No tienes permisos para eliminar del inventario.")
            return redirect('inventory_management:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper