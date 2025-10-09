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
    """Lista de productos con datos reales"""
    from apps.inventory_management.models import Producto, Categoria
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    productos = Producto.objects.select_related('categoria', 'proveedor', 'unidad_medida_base').filter(activo=True).order_by('nombre')
    
    # Filtros
    search = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    
    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) | 
            Q(codigo_barras__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    
    if tipo:
        productos = productos.filter(tipo_inventario=tipo)
    
    # Obtener todas las categorías para el filtro
    categorias = Categoria.objects.filter(activa=True).order_by('nombre')
    
    # Paginación
    paginator = Paginator(productos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'productos': page_obj,
        'page_obj': page_obj,
        'categorias': categorias,
        'search': search,
        'categoria_selected': categoria_id,
        'tipo_selected': tipo,
    }
    
    return render(request, 'custom_admin/inventario/productos_list.html', context)

@ensure_csrf_cookie
@auth_required
def producto_detail_view(request, pk):
    """Detalle de producto"""
    return render(request, 'custom_admin/inventario/producto_detail.html', {'producto_id': pk})

@ensure_csrf_cookie
@auth_required
def producto_crear(request):
    """Crear nuevo producto"""
    from apps.inventory_management.models import Producto
    from apps.authentication.models import Usuario
    from django.contrib import messages
    
    if request.method == 'POST':
        try:
            # ✅ OBTENER EL PRIMER USUARIO ADMIN DISPONIBLE
            usuario = Usuario.objects.filter(rol='ADMIN').first()
            
            if not usuario:
                # Si no hay admin, usa cualquier usuario
                usuario = Usuario.objects.first()
            
            if not usuario:
                messages.error(request, 'No hay usuarios en el sistema.')
                return redirect('custom_admin:productos')
            
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            categoria_id = request.POST.get('categoria', '').strip()
            tipo_inventario = request.POST.get('tipo_inventario', 'NORMAL')
            activo = request.POST.get('activo') == 'on'
            
            # Validar nombre
            if not nombre:
                messages.error(request, 'El nombre del producto es obligatorio')
                return redirect('custom_admin:productos')
            
            # ✅ CREAR PRODUCTO CON TODOS LOS CAMPOS OBLIGATORIOS
            producto_data = {
                'nombre': nombre,
                'descripcion': descripcion,
                'tipo_inventario': tipo_inventario,
                'activo': activo,
                'usuario_registro': usuario,  # ✅ CAMPO OBLIGATORIO
            }
            
            # Agregar categoría si existe
            if categoria_id:
                producto_data['categoria_id'] = categoria_id
            
            # Agregar precios según el tipo
            if tipo_inventario == 'QUINTAL':
                precio_peso = request.POST.get('precio_por_unidad_peso', '0').strip()
                producto_data['precio_por_unidad_peso'] = float(precio_peso) if precio_peso else 0.0
            else:  # NORMAL
                precio_unit = request.POST.get('precio_unitario', '0').strip()
                producto_data['precio_unitario'] = float(precio_unit) if precio_unit else 0.0
            
            # Crear el producto
            producto = Producto.objects.create(**producto_data)
            
            messages.success(request, f'✅ Producto "{producto.nombre}" creado exitosamente')
            
        except ValueError as e:
            messages.error(request, f'Error en los datos numéricos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear producto: {str(e)}')
    
    return redirect('custom_admin:productos')

@ensure_csrf_cookie
@auth_required
def producto_editar(request, producto_id):
    """Editar producto existente"""
    from apps.inventory_management.models import Producto
    from apps.authentication.models import Usuario
    from django.contrib import messages
    
    try:
        producto = Producto.objects.get(id=producto_id)
        
        if request.method == 'POST':
            # ✅ OBTENER EL PRIMER USUARIO ADMIN DISPONIBLE
            usuario = Usuario.objects.filter(rol='ADMIN').first()
            
            if not usuario:
                usuario = Usuario.objects.first()
            
            if not usuario:
                messages.error(request, 'No hay usuarios en el sistema.')
                return redirect('custom_admin:productos')
            
            # Actualizar campos
            nombre = request.POST.get('nombre', '').strip()
            if not nombre:
                messages.error(request, 'El nombre del producto es obligatorio')
                return redirect('custom_admin:productos')
            
            producto.nombre = nombre
            producto.descripcion = request.POST.get('descripcion', '').strip()
            
            categoria_id = request.POST.get('categoria', '').strip()
            producto.categoria_id = categoria_id if categoria_id else None
            
            tipo_inventario = request.POST.get('tipo_inventario', 'NORMAL')
            producto.tipo_inventario = tipo_inventario
            
            # Actualizar precios según el tipo
            if tipo_inventario == 'QUINTAL':
                precio_peso = request.POST.get('precio_por_unidad_peso', '0').strip()
                producto.precio_por_unidad_peso = float(precio_peso) if precio_peso else 0.0
                producto.precio_unitario = None
            else:  # NORMAL
                precio_unit = request.POST.get('precio_unitario', '0').strip()
                producto.precio_unitario = float(precio_unit) if precio_unit else 0.0
                producto.precio_por_unidad_peso = None
            
            producto.activo = request.POST.get('activo') == 'on'
            
            # ✅ ESTABLECER USUARIO DE MODIFICACIÓN
            producto.usuario_modificacion = usuario
            
            producto.save()
            
            messages.success(request, f'✅ Producto "{producto.nombre}" actualizado exitosamente')
            return redirect('custom_admin:productos')
            
    except Producto.DoesNotExist:
        messages.error(request, '❌ Producto no encontrado')
        return redirect('custom_admin:productos')
    except ValueError as e:
        messages.error(request, f'Error en los datos numéricos: {str(e)}')
        return redirect('custom_admin:productos')
    except Exception as e:
        messages.error(request, f'Error al editar producto: {str(e)}')
    
    return redirect('custom_admin:productos')

@ensure_csrf_cookie
@auth_required
def producto_eliminar(request, producto_id):
    """Eliminar producto"""
    from apps.inventory_management.models import Producto
    from django.contrib import messages
    
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=producto_id)
            nombre = producto.nombre
            producto.delete()
            messages.success(request, f'✅ Producto "{nombre}" eliminado exitosamente')
        except Producto.DoesNotExist:
            messages.error(request, '❌ Producto no encontrado')
        except Exception as e:
            messages.error(request, f'Error al eliminar producto: {str(e)}')
    
    return redirect('custom_admin:productos')

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
    """Lista de categorías con datos reales"""
    from apps.inventory_management.models import Categoria
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    categorias = Categoria.objects.all().order_by('orden', 'nombre')
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        categorias = categorias.filter(
            Q(nombre__icontains=search) | 
            Q(descripcion__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(categorias, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categorias': page_obj,
        'page_obj': page_obj,
        'search': search,
    }
    
    return render(request, 'custom_admin/inventario/categorias_list.html', context)

@ensure_csrf_cookie
@auth_required
def categoria_crear_view(request):
    """Crear categoría"""
    from apps.inventory_management.models import Categoria
    from django.contrib import messages
    
    if request.method == 'POST':
        try:
            categoria = Categoria.objects.create(
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                margen_ganancia_sugerido=request.POST.get('margen_ganancia_sugerido', 30.00),
                descuento_maximo_permitido=request.POST.get('descuento_maximo_permitido', 10.00),
                orden=request.POST.get('orden', 0),
                activa=request.POST.get('activa') == 'on'
            )
            messages.success(request, f'Categoría "{categoria.nombre}" creada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al crear la categoría: {str(e)}')
    
    return redirect('custom_admin:categorias')

@ensure_csrf_cookie
@auth_required
def categoria_editar_view(request, pk):
    """Editar categoría"""
    from apps.inventory_management.models import Categoria
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        try:
            categoria.nombre = request.POST.get('nombre')
            categoria.descripcion = request.POST.get('descripcion', '')
            categoria.margen_ganancia_sugerido = request.POST.get('margen_ganancia_sugerido', 30.00)
            categoria.descuento_maximo_permitido = request.POST.get('descuento_maximo_permitido', 10.00)
            categoria.orden = request.POST.get('orden', 0)
            categoria.activa = request.POST.get('activa') == 'on'
            categoria.save()
            messages.success(request, f'Categoría "{categoria.nombre}" actualizada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar la categoría: {str(e)}')
    
    return redirect('custom_admin:categorias')

@ensure_csrf_cookie
@auth_required
def categoria_eliminar_view(request, pk):
    """Eliminar categoría"""
    from apps.inventory_management.models import Categoria
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        nombre = categoria.nombre
        try:
            # Verificar si tiene productos asociados
            if categoria.productos.exists():
                messages.error(request, f'No se puede eliminar la categoría "{nombre}" porque tiene productos asociados.')
            else:
                categoria.delete()
                messages.success(request, f'Categoría "{nombre}" eliminada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar la categoría: {str(e)}')
    
    return redirect('custom_admin:categorias')

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