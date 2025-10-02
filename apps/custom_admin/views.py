"""
Views del Panel Administrativo Personalizado
Solo sirven HTML, la lógica está en JavaScript con JWT
"""

from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.utils import timezone
from functools import wraps


# ========================================
# DECORATOR DE AUTENTICACIÓN
# ========================================

def auth_required(view_func):
    """
    Decorator para vistas que requieren autenticación.
    La verificación real se hace en JavaScript con JWT.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


# ========================================
# DASHBOARD
# ========================================

@ensure_csrf_cookie
@auth_required
def dashboard_view(request):
    """Dashboard principal del panel admin"""
    return render(request, 'custom_admin/dashboard.html')


# ========================================
# GESTIÓN DE USUARIOS
# ========================================

@ensure_csrf_cookie
@auth_required
def usuarios_view(request):
    """Lista de usuarios"""
    return render(request, 'custom_admin/usuarios/usuarios.html')


# ========================================
# ROLES Y PERMISOS
# ========================================

@ensure_csrf_cookie
@auth_required
def roles_view(request):
    """Lista de roles disponibles"""
    return render(request, 'custom_admin/roles/list.html')


# ========================================
# INVENTARIO
# ========================================

@ensure_csrf_cookie
@auth_required
def inventario_dashboard_view(request):
    """Dashboard de inventario"""
    return render(request, 'custom_admin/inventario/dashboard.html')

@ensure_csrf_cookie
@auth_required
def productos_view(request):
    """Lista de productos"""
    return render(request, 'custom_admin/inventario/productos_list.html')

@ensure_csrf_cookie
@auth_required
def producto_detail_view(request, pk):
    """Detalle de producto"""
    return render(request, 'custom_admin/inventario/producto_detail.html', {'producto_id': pk})

@ensure_csrf_cookie
@auth_required
def quintales_view(request):
    """Lista de quintales"""
    return render(request, 'custom_admin/inventario/quintales_list.html')

@ensure_csrf_cookie
@auth_required
def quintal_detail_view(request, pk):
    """Detalle de quintal"""
    return render(request, 'custom_admin/inventario/quintal_detail.html', {'quintal_id': pk})

@ensure_csrf_cookie
@auth_required
def categorias_view(request):
    """Lista de categorías"""
    return render(request, 'custom_admin/inventario/categorias_list.html')

@ensure_csrf_cookie
@auth_required
def proveedores_view(request):
    """Lista de proveedores"""
    return render(request, 'custom_admin/inventario/proveedores_list.html')


# ========================================
# VENTAS
# ========================================

@ensure_csrf_cookie
@auth_required
def ventas_dashboard_view(request):
    """Dashboard de ventas"""
    return render(request, 'custom_admin/ventas/dashboard.html')

@ensure_csrf_cookie
@auth_required
def ventas_view(request):
    """Historial de ventas"""
    return render(request, 'custom_admin/ventas/list.html')

@ensure_csrf_cookie
@auth_required
def venta_detail_view(request, pk):
    """Detalle de venta"""
    return render(request, 'custom_admin/ventas/detail.html', {'venta_id': pk})

@ensure_csrf_cookie
@auth_required
def clientes_view(request):
    """Lista de clientes"""
    return render(request, 'custom_admin/ventas/clientes_list.html')

@ensure_csrf_cookie
@auth_required
def devoluciones_view(request):
    """Lista de devoluciones"""
    return render(request, 'custom_admin/ventas/devoluciones_list.html')


# ========================================
# FINANZAS
# ========================================

@ensure_csrf_cookie
@auth_required
def finanzas_dashboard_view(request):
    """Dashboard financiero"""
    return render(request, 'custom_admin/finanzas/dashboard.html')

@ensure_csrf_cookie
@auth_required
def cajas_view(request):
    """Lista de cajas"""
    return render(request, 'custom_admin/finanzas/cajas_list.html')

@ensure_csrf_cookie
@auth_required
def caja_detail_view(request, pk):
    """Detalle de caja"""
    return render(request, 'custom_admin/finanzas/caja_detail.html', {'caja_id': pk})

@ensure_csrf_cookie
@auth_required
def arqueos_view(request):
    """Lista de arqueos"""
    return render(request, 'custom_admin/finanzas/arqueos_list.html')

@ensure_csrf_cookie
@auth_required
def caja_chica_view(request):
    """Lista de cajas chicas"""
    return render(request, 'custom_admin/finanzas/caja_chica_list.html')


# ========================================
# REPORTES
# ========================================

@ensure_csrf_cookie
@auth_required
def reportes_dashboard_view(request):
    """Dashboard de reportes"""
    return render(request, 'custom_admin/reportes/dashboard.html')

@ensure_csrf_cookie
@auth_required
def reporte_ventas_view(request):
    """Reporte de ventas"""
    return render(request, 'custom_admin/reportes/ventas.html')

@ensure_csrf_cookie
@auth_required
def reporte_inventario_view(request):
    """Reporte de inventario"""
    return render(request, 'custom_admin/reportes/inventario.html')

@ensure_csrf_cookie
@auth_required
def reporte_financiero_view(request):
    """Reporte financiero"""
    return render(request, 'custom_admin/reportes/financiero.html')


# ========================================
# ALERTAS
# ========================================

@ensure_csrf_cookie
@auth_required
def alertas_view(request):
    """Dashboard de alertas"""
    return render(request, 'custom_admin/alertas/dashboard.html')


# ========================================
# LOGS Y AUDITORÍA
# ========================================

@ensure_csrf_cookie
@auth_required
def logs_view(request):
    """Lista de logs"""
    return render(request, 'custom_admin/logs/list.html')

@ensure_csrf_cookie
@auth_required
def logs_accesos_view(request):
    """Logs de acceso"""
    return render(request, 'custom_admin/logs/accesos.html')


# ========================================
# SESIONES
# ========================================

@ensure_csrf_cookie
@auth_required
def sesiones_view(request):
    """Sesiones activas"""
    return render(request, 'custom_admin/sesiones/activas.html')


# ========================================
# CONFIGURACIÓN
# ========================================

@ensure_csrf_cookie
@auth_required
def configuracion_view(request):
    """Configuración general del sistema"""
    return render(request, 'custom_admin/configuracion/general.html')

@ensure_csrf_cookie
@auth_required
def config_empresa_view(request):
    """Configuración de empresa"""
    return render(request, 'custom_admin/configuracion/empresa.html')

@ensure_csrf_cookie
@auth_required
def config_facturacion_view(request):
    """Configuración de facturación"""
    return render(request, 'custom_admin/configuracion/facturacion.html')


# ========================================
# BÚSQUEDA GLOBAL
# ========================================

@ensure_csrf_cookie
@auth_required
def busqueda_view(request):
    """Búsqueda global"""
    query = request.GET.get('q', '')
    return render(request, 'custom_admin/busqueda/results.html', {'query': query})


# ========================================
# NOTIFICACIONES
# ========================================

@ensure_csrf_cookie
@auth_required
def notificaciones_view(request):
    """Centro de notificaciones"""
    return render(request, 'custom_admin/notificaciones/list.html')


# ========================================
# PERFIL
# ========================================

@ensure_csrf_cookie
@auth_required
def perfil_view(request):
    """Perfil del usuario actual"""
    return render(request, 'custom_admin/perfil/view.html')

@ensure_csrf_cookie
@auth_required
def perfil_editar_view(request):
    """Editar perfil"""
    return render(request, 'custom_admin/perfil/edit.html')

@ensure_csrf_cookie
@auth_required
def perfil_cambiar_password_view(request):
    """Cambiar contraseña"""
    return render(request, 'custom_admin/perfil/change_password.html')


# ========================================
# APIs MOCK PARA DASHBOARD (TEMPORALES)
# ========================================

@ensure_csrf_cookie
def api_dashboard_stats(request):
    """Estadísticas del dashboard - MOCK temporal"""
    return JsonResponse({
        'ventas_hoy': 1250.50,
        'num_ventas': 15,
        'productos_total': 250,
        'alertas_criticas': 3,
        'ventas_semana': [
            {'fecha': '2025-10-27', 'total': 1500},
            {'fecha': '2025-10-28', 'total': 1800},
            {'fecha': '2025-10-29', 'total': 2100},
            {'fecha': '2025-10-30', 'total': 1900},
            {'fecha': '2025-10-31', 'total': 2300},
            {'fecha': '2025-11-01', 'total': 2500},
            {'fecha': '2025-11-02', 'total': 1250.50},
        ],
        'top_productos': [
            {'nombre': 'Arroz', 'cantidad': 50},
            {'nombre': 'Frijol', 'cantidad': 30},
            {'nombre': 'Azúcar', 'cantidad': 25},
        ],
        'ultimas_ventas': [
            {
                'numero_venta': 'VNT-2025-00001',
                'cliente': 'Juan Pérez',
                'total': 50.00,
                'estado': 'COMPLETADA'
            },
        ],
        'alertas': [
            {
                'titulo': 'Stock bajo en Arroz',
                'mensaje': 'Solo quedan 5 unidades',
                'prioridad': 'ALTA'
            },
        ]
    })


# ========================================
# UTILIDADES
# ========================================

def health_check_view(request):
    """Health check del panel"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    })