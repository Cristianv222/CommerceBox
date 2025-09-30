from django.shortcuts import render

# Create your views here.
"""
Views para el frontend con Django Templates
Solo sirven HTML, la lógica está en JavaScript con JWT
"""

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def login_view(request):
    """Página de login"""
    return render(request, 'authentication/login.html')

@ensure_csrf_cookie
def dashboard_view(request):
    """Dashboard principal"""
    return render(request, 'dashboard/dashboard.html')

@ensure_csrf_cookie
def inventario_view(request):
    """Listado de inventario"""
    return render(request, 'inventory/list.html')

@ensure_csrf_cookie
def ventas_view(request):
    """Punto de venta"""
    return render(request, 'sales/pos.html')

@ensure_csrf_cookie
def reportes_view(request):
    """Reportes y analytics"""
    return render(request, 'reports/dashboard.html')

@ensure_csrf_cookie
def perfil_view(request):
    """Perfil de usuario"""
    return render(request, 'authentication/perfil.html')