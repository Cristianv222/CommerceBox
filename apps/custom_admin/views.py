"""
Views del Panel Administrativo Personalizado
Solo sirven HTML, la lógica está en JavaScript con JWT
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from functools import wraps
from apps.inventory_management.models import Marca

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
    """Lista de productos con datos reales - VERSIÓN CORREGIDA"""
    from apps.inventory_management.models import Producto, Categoria, Marca, Quintal, UnidadMedida  # ✅ AGREGAR UnidadMedida
    from apps.system_configuration.models import ConfiguracionSistema
    from django.db.models import Q, Prefetch
    from django.core.paginator import Paginator
    
    # ✅ SOLUCIÓN: Usar prefetch_related para cargar quintales e inventario normal
    productos = Producto.objects.select_related(
        'categoria', 
        'proveedor', 
        'unidad_medida_base', 
        'marca'
    ).prefetch_related(
        Prefetch(
            'quintales',
            queryset=Quintal.objects.filter(estado='DISPONIBLE').order_by('fecha_recepcion')
        ),
        'inventario_normal'
    ).filter(activo=True).order_by('nombre')
    
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
    
    # Obtener todas las categorías, marcas y ✅ UNIDADES DE MEDIDA para los filtros
    categorias = Categoria.objects.filter(activa=True).order_by('nombre')
    marcas = Marca.objects.filter(activa=True).order_by('nombre')
    unidades_medida = UnidadMedida.objects.filter(activa=True).order_by('orden_display')  # ✅ AGREGAR ESTA LÍNEA
    
    # ✅ OBTENER IVA DEFAULT DEL SISTEMA
    config = ConfiguracionSistema.get_config()
    iva_default = config.iva_default
    
    # Paginación
    paginator = Paginator(productos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'productos': page_obj,
        'page_obj': page_obj,
        'marcas': marcas,
        'categorias': categorias,
        'unidades_medida': unidades_medida,  # ✅ AGREGAR ESTA LÍNEA AL CONTEXTO
        'search': search,
        'categoria_selected': categoria_id,
        'tipo_selected': tipo,
        'iva_default': iva_default,
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
    from decimal import Decimal
    
    if request.method == 'POST':
        try:
            usuario = Usuario.objects.filter(rol__codigo='ADMIN').first()
            
            if not usuario:
                usuario = Usuario.objects.first()
            
            if not usuario:
                messages.error(request, 'No hay usuarios en el sistema.')
                return redirect('custom_admin:productos')
            
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            categoria_id = request.POST.get('categoria', '').strip()
            marca_id = request.POST.get('marca', '').strip()  # ✅ AGREGAR MARCA
            tipo_inventario = request.POST.get('tipo_inventario', 'NORMAL')
            activo = request.POST.get('activo') == 'on'
            iva_value = request.POST.get('iva', '0').strip()  # ✅ OBTENER IVA
            
            if not nombre:
                messages.error(request, 'El nombre del producto es obligatorio')
                return redirect('custom_admin:productos')
            
            producto_data = {
                'nombre': nombre,
                'descripcion': descripcion,
                'tipo_inventario': tipo_inventario,
                'activo': activo,
                'usuario_registro': usuario,
                'iva': Decimal(iva_value) if iva_value else Decimal('0.00'),  # ✅ AGREGAR IVA
            }
            
            if categoria_id:
                producto_data['categoria_id'] = categoria_id
            
            # ✅ AGREGAR MARCA SI EXISTE
            if marca_id:
                producto_data['marca_id'] = marca_id
            
            # ✅ MANEJAR IMAGEN
            if 'imagen' in request.FILES:
                producto_data['imagen'] = request.FILES['imagen']
            
            if tipo_inventario == 'QUINTAL':
                precio_peso = request.POST.get('precio_por_unidad_peso', '0').strip()
                producto_data['precio_por_unidad_peso'] = Decimal(precio_peso) if precio_peso else Decimal('0.00')
            else:
                precio_unit = request.POST.get('precio_unitario', '0').strip()
                producto_data['precio_unitario'] = Decimal(precio_unit) if precio_unit else Decimal('0.00')
            
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
    from decimal import Decimal
    
    try:
        producto = Producto.objects.get(id=producto_id)
        
        if request.method == 'POST':
            usuario = Usuario.objects.filter(rol__codigo='ADMIN').first()
            
            if not usuario:
                usuario = Usuario.objects.first()
            
            if not usuario:
                messages.error(request, 'No hay usuarios en el sistema.')
                return redirect('custom_admin:productos')
            
            nombre = request.POST.get('nombre', '').strip()
            if not nombre:
                messages.error(request, 'El nombre del producto es obligatorio')
                return redirect('custom_admin:productos')
            
            producto.nombre = nombre
            producto.descripcion = request.POST.get('descripcion', '').strip()
            
            categoria_id = request.POST.get('categoria', '').strip()
            producto.categoria_id = categoria_id if categoria_id else None
            
            # ✅ ACTUALIZAR MARCA
            marca_id = request.POST.get('marca', '').strip()
            producto.marca_id = marca_id if marca_id else None
            
            # ✅ ACTUALIZAR IVA
            iva_value = request.POST.get('iva', '0').strip()
            producto.iva = Decimal(iva_value) if iva_value else Decimal('0.00')
            
            # ✅ ACTUALIZAR IMAGEN SI SE SUBE UNA NUEVA
            if 'imagen' in request.FILES:
                producto.imagen = request.FILES['imagen']
            
            tipo_inventario = request.POST.get('tipo_inventario', 'NORMAL')
            producto.tipo_inventario = tipo_inventario
            
            if tipo_inventario == 'QUINTAL':
                precio_peso = request.POST.get('precio_por_unidad_peso', '0').strip()
                producto.precio_por_unidad_peso = Decimal(precio_peso) if precio_peso else Decimal('0.00')
                producto.precio_unitario = None
            else:
                precio_unit = request.POST.get('precio_unitario', '0').strip()
                producto.precio_unitario = Decimal(precio_unit) if precio_unit else Decimal('0.00')
                producto.precio_por_unidad_peso = None
            
            producto.activo = request.POST.get('activo') == 'on'
            
            if hasattr(producto, 'usuario_modificacion'):
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
    """Eliminar o desactivar producto"""
    from apps.inventory_management.models import Producto
    from django.http import HttpResponseRedirect
    from django.db.models import ProtectedError
    
    try:
        producto = Producto.objects.get(id=producto_id)
        nombre = producto.nombre
        
        # Verificar todas las relaciones protegidas
        tiene_relaciones = (
            producto.detalleventa_set.exists() or 
            producto.detallecompra_set.exists() or
            producto.quintales.exists()
        )
        
        if tiene_relaciones:
            # Tiene relaciones, solo desactivar
            producto.activo = False
            producto.save()
            messages.warning(
                request, 
                f'El producto "{nombre}" tiene registros asociados (ventas, compras o quintales) y no puede eliminarse. Se ha desactivado.'
            )
        else:
            # No tiene relaciones, eliminar
            try:
                producto.delete()
                messages.success(request, f'Producto "{nombre}" eliminado correctamente.')
            except ProtectedError as e:
                # Si aún así hay error, desactivar
                producto.activo = False
                producto.save()
                messages.warning(
                    request, 
                    f'El producto "{nombre}" tiene registros asociados y no puede eliminarse. Se ha desactivado.'
                )
        
        return HttpResponseRedirect('/panel/inventario/productos/')
        
    except Producto.DoesNotExist:
        messages.error(request, 'Producto no encontrado.')
        return HttpResponseRedirect('/panel/inventario/productos/')
    except Exception as e:
        messages.error(request, f'Error al procesar producto: {str(e)}')
        return HttpResponseRedirect('/panel/inventario/productos/')

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
    
    search = request.GET.get('search', '')
    if search:
        categorias = categorias.filter(
            Q(nombre__icontains=search) | 
            Q(descripcion__icontains=search)
        )
    
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
    
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        nombre = categoria.nombre
        try:
            if categoria.productos.exists():
                messages.error(request, f'No se puede eliminar la categoría "{nombre}" porque tiene productos asociados.')
            else:
                categoria.delete()
                messages.success(request, f'Categoría "{nombre}" eliminada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar la categoría: {str(e)}')
    
    return redirect('custom_admin:categorias')


# ============================================================================
# VISTAS DE MARCAS - ✅ VERSIÓN CORREGIDA
# ============================================================================

@ensure_csrf_cookie
@auth_required
def marcas_list(request):
    """Lista todas las marcas de productos con filtros y paginación"""
    from apps.inventory_management.models import Marca
    from django.core.paginator import Paginator
    from django.db.models import Q, Count
    
    marcas = Marca.objects.annotate(
        total_productos=Count('productos', distinct=True),
        productos_con_stock=Count(
            'productos',
            filter=Q(
                productos__activo=True,
                productos__tipo_inventario='NORMAL',
                productos__inventario_normal__stock_actual__gt=0
            ),
            distinct=True
        )
    ).order_by('orden', 'nombre')
    
    # Filtros
    search = request.GET.get('search', '')
    destacada_selected = request.GET.get('destacada', '')
    pais_selected = request.GET.get('pais', '')
    
    if search:
        marcas = marcas.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(fabricante__icontains=search)
        )
    
    if destacada_selected:
        marcas = marcas.filter(destacada=True)
    
    if pais_selected:
        marcas = marcas.filter(pais_origen=pais_selected)
    
    # Obtener lista de países únicos para el filtro
    paises = Marca.objects.exclude(
        pais_origen__isnull=True
    ).exclude(
        pais_origen=''
    ).values_list('pais_origen', flat=True).distinct().order_by('pais_origen')
    
    # Paginación
    paginator = Paginator(marcas, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'marcas': page_obj,
        'page_obj': page_obj,
        'paises': paises,
        'search': search,
        'destacada_selected': destacada_selected,
        'pais_selected': pais_selected,
    }
    
    return render(request, 'custom_admin/inventario/marcas_list.html', context)


@ensure_csrf_cookie
@auth_required
def marca_crear(request):
    """Crear una nueva marca - VERSIÓN COMPLETA"""
    from apps.inventory_management.models import Marca
    
    if request.method == 'POST':
        try:
            # ✅ Obtener todos los campos del formulario
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            pais_origen = request.POST.get('pais_origen', '').strip()
            fabricante = request.POST.get('fabricante', '').strip()
            sitio_web = request.POST.get('sitio_web', '').strip()
            orden = request.POST.get('orden', '0')
            
            # ✅ Campos booleanos (checkbox)
            activa = request.POST.get('activa') == 'on'
            destacada = request.POST.get('destacada') == 'on'
            
            # ✅ Archivo de logo (si existe)
            logo = request.FILES.get('logo')
            
            # Validación básica
            if not nombre:
                messages.error(request, '❌ El nombre de la marca es obligatorio.')
                return redirect('custom_admin:marcas')
            
            # Verificar si ya existe
            if Marca.objects.filter(nombre__iexact=nombre).exists():
                messages.error(request, f'❌ Ya existe una marca con el nombre "{nombre}".')
                return redirect('custom_admin:marcas')
            
            # ✅ Crear la marca con TODOS los campos
            marca_data = {
                'nombre': nombre,
                'descripcion': descripcion,
                'pais_origen': pais_origen,
                'fabricante': fabricante,
                'sitio_web': sitio_web,
                'activa': activa,
                'destacada': destacada,
                'orden': int(orden) if orden else 0,
            }
            
            # ✅ Agregar logo si existe
            if logo:
                marca_data['logo'] = logo
            
            marca = Marca.objects.create(**marca_data)
            
            messages.success(
                request, 
                f'✅ Marca "{marca.nombre}" creada exitosamente.'
            )
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear la marca: {str(e)}')
    
    return redirect('custom_admin:marcas')


@ensure_csrf_cookie
@auth_required
def marca_editar(request, pk):
    """Editar una marca existente - VERSIÓN COMPLETA"""
    from apps.inventory_management.models import Marca
    
    marca = get_object_or_404(Marca, pk=pk)
    
    if request.method == 'POST':
        try:
            # ✅ Actualizar todos los campos
            nombre = request.POST.get('nombre', '').strip()
            
            if not nombre:
                messages.error(request, '❌ El nombre de la marca es obligatorio.')
                return redirect('custom_admin:marcas')
            
            # Verificar duplicados (excluyendo la marca actual)
            if Marca.objects.filter(nombre__iexact=nombre).exclude(pk=pk).exists():
                messages.error(request, f'❌ Ya existe otra marca con el nombre "{nombre}".')
                return redirect('custom_admin:marcas')
            
            # ✅ Actualizar campos
            marca.nombre = nombre
            marca.descripcion = request.POST.get('descripcion', '').strip()
            marca.pais_origen = request.POST.get('pais_origen', '').strip()
            marca.fabricante = request.POST.get('fabricante', '').strip()
            marca.sitio_web = request.POST.get('sitio_web', '').strip()
            marca.orden = int(request.POST.get('orden', '0'))
            marca.activa = request.POST.get('activa') == 'on'
            marca.destacada = request.POST.get('destacada') == 'on'
            
            # ✅ Actualizar logo si se subió uno nuevo
            logo = request.FILES.get('logo')
            if logo:
                # Eliminar logo anterior si existe
                if marca.logo:
                    marca.logo.delete(save=False)
                marca.logo = logo
            
            marca.save()
            
            messages.success(
                request, 
                f'✅ Marca "{marca.nombre}" actualizada exitosamente.'
            )
            
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar la marca: {str(e)}')
    
    return redirect('custom_admin:marcas')


@ensure_csrf_cookie
@auth_required
def marca_eliminar(request, pk):
    """Eliminar una marca (o desactivar si tiene productos)"""
    from apps.inventory_management.models import Marca
    
    marca = get_object_or_404(Marca, pk=pk)
    nombre = marca.nombre
    
    if request.method == 'POST':
        try:
            # Verificar si tiene productos asociados
            if marca.productos.exists():
                # Tiene productos, solo desactivar
                marca.activa = False
                marca.save()
                messages.warning(
                    request,
                    f'⚠️ La marca "{nombre}" tiene productos asociados y no puede eliminarse. Se ha desactivado.'
                )
            else:
                # No tiene productos, eliminar completamente
                marca.delete()
                messages.success(
                    request,
                    f'✅ Marca "{nombre}" eliminada exitosamente.'
                )
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar la marca: {str(e)}')
    
    return redirect('custom_admin:marcas')

# ============================================================================
# PROVEEDORES - MÓDULO COMPLETO CORREGIDO
# ============================================================================

@ensure_csrf_cookie
@auth_required
def proveedores_view(request):
    """Lista de proveedores con datos reales"""
    from apps.inventory_management.models import Proveedor
    from django.db.models import Q, Count
    from django.core.paginator import Paginator
    
    proveedores = Proveedor.objects.annotate(
        total_productos=Count('productos', distinct=True)
    ).order_by('nombre_comercial')
    
    # Filtros
    search = request.GET.get('search', '')
    activo_selected = request.GET.get('activo', '')
    
    if search:
        proveedores = proveedores.filter(
            Q(nombre_comercial__icontains=search) |
            Q(razon_social__icontains=search) |
            Q(ruc_nit__icontains=search) |
            Q(email__icontains=search)
        )
    
    if activo_selected:
        proveedores = proveedores.filter(activo=(activo_selected == 'true'))
    
    # Paginación
    paginator = Paginator(proveedores, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'proveedores': page_obj,
        'page_obj': page_obj,
        'search': search,
        'activo_selected': activo_selected,
    }
    
    return render(request, 'custom_admin/inventario/proveedores_list.html', context)


@ensure_csrf_cookie
@auth_required
def proveedor_crear(request):
    """Crear un nuevo proveedor"""
    from apps.inventory_management.models import Proveedor
    from decimal import Decimal
    
    if request.method == 'POST':
        try:
            nombre_comercial = request.POST.get('nombre_comercial', '').strip()
            ruc_nit = request.POST.get('ruc_nit', '').strip()
            
            if not nombre_comercial:
                messages.error(request, '❌ El nombre comercial es obligatorio.')
                return redirect('custom_admin:proveedores')
            
            if not ruc_nit:
                messages.error(request, '❌ El RUC/NIT es obligatorio.')
                return redirect('custom_admin:proveedores')
            
            # Verificar si ya existe por nombre
            if Proveedor.objects.filter(nombre_comercial__iexact=nombre_comercial).exists():
                messages.error(request, f'❌ Ya existe un proveedor con el nombre "{nombre_comercial}".')
                return redirect('custom_admin:proveedores')
            
            # Verificar si ya existe por RUC
            if Proveedor.objects.filter(ruc_nit=ruc_nit).exists():
                messages.error(request, f'❌ Ya existe un proveedor con el RUC/NIT "{ruc_nit}".')
                return redirect('custom_admin:proveedores')
            
            # Preparar datos
            dias_credito = request.POST.get('dias_credito', '0').strip()
            limite_credito = request.POST.get('limite_credito', '0').strip()
            
            proveedor = Proveedor.objects.create(
                nombre_comercial=nombre_comercial,
                razon_social=request.POST.get('razon_social', '').strip(),
                ruc_nit=ruc_nit,
                direccion=request.POST.get('direccion', '').strip(),
                telefono=request.POST.get('telefono', '').strip(),
                email=request.POST.get('email', '').strip(),
                dias_credito=int(dias_credito) if dias_credito else 0,
                limite_credito=Decimal(limite_credito) if limite_credito else Decimal('0.00'),
                activo=request.POST.get('activo') == 'on'
            )
            
            messages.success(request, f'✅ Proveedor "{proveedor.nombre_comercial}" creado exitosamente.')
            
        except ValueError as e:
            messages.error(request, f'❌ Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'❌ Error al crear el proveedor: {str(e)}')
            import traceback
            traceback.print_exc()
    
    return redirect('custom_admin:proveedores')


@ensure_csrf_cookie
@auth_required
def proveedor_editar(request, pk):
    """Editar un proveedor existente"""
    from apps.inventory_management.models import Proveedor
    from decimal import Decimal
    
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre_comercial = request.POST.get('nombre_comercial', '').strip()
            ruc_nit = request.POST.get('ruc_nit', '').strip()
            
            if not nombre_comercial:
                messages.error(request, '❌ El nombre comercial es obligatorio.')
                return redirect('custom_admin:proveedores')
            
            if not ruc_nit:
                messages.error(request, '❌ El RUC/NIT es obligatorio.')
                return redirect('custom_admin:proveedores')
            
            # Verificar duplicados por nombre (excluyendo el proveedor actual)
            if Proveedor.objects.filter(nombre_comercial__iexact=nombre_comercial).exclude(pk=pk).exists():
                messages.error(request, f'❌ Ya existe otro proveedor con el nombre "{nombre_comercial}".')
                return redirect('custom_admin:proveedores')
            
            # Verificar duplicados por RUC (excluyendo el proveedor actual)
            if Proveedor.objects.filter(ruc_nit=ruc_nit).exclude(pk=pk).exists():
                messages.error(request, f'❌ Ya existe otro proveedor con el RUC/NIT "{ruc_nit}".')
                return redirect('custom_admin:proveedores')
            
            # Actualizar campos
            proveedor.nombre_comercial = nombre_comercial
            proveedor.razon_social = request.POST.get('razon_social', '').strip()
            proveedor.ruc_nit = ruc_nit
            proveedor.direccion = request.POST.get('direccion', '').strip()
            proveedor.telefono = request.POST.get('telefono', '').strip()
            proveedor.email = request.POST.get('email', '').strip()
            
            dias_credito = request.POST.get('dias_credito', '0').strip()
            limite_credito = request.POST.get('limite_credito', '0').strip()
            
            proveedor.dias_credito = int(dias_credito) if dias_credito else 0
            proveedor.limite_credito = Decimal(limite_credito) if limite_credito else Decimal('0.00')
            proveedor.activo = request.POST.get('activo') == 'on'
            
            proveedor.save()
            
            messages.success(request, f'✅ Proveedor "{proveedor.nombre_comercial}" actualizado exitosamente.')
            
        except ValueError as e:
            messages.error(request, f'❌ Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar el proveedor: {str(e)}')
            import traceback
            traceback.print_exc()
    
    return redirect('custom_admin:proveedores')


@ensure_csrf_cookie
@auth_required
def proveedor_eliminar(request, pk):
    """Eliminar un proveedor (o desactivar si tiene productos)"""
    from apps.inventory_management.models import Proveedor
    
    proveedor = get_object_or_404(Proveedor, pk=pk)
    nombre = proveedor.nombre_comercial
    
    if request.method == 'POST':
        try:
            # Verificar si tiene productos asociados
            if proveedor.productos.exists():
                # Tiene productos, solo desactivar
                proveedor.activo = False
                proveedor.save()
                messages.warning(
                    request,
                    f'⚠️ El proveedor "{nombre}" tiene {proveedor.productos.count()} productos asociados y no puede eliminarse. Se ha desactivado.'
                )
            else:
                # No tiene productos, eliminar completamente
                proveedor.delete()
                messages.success(request, f'✅ Proveedor "{nombre}" eliminado exitosamente.')
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar el proveedor: {str(e)}')
            import traceback
            traceback.print_exc()
    
    return redirect('custom_admin:proveedores')


@ensure_csrf_cookie
@auth_required
def proveedor_detalle_api(request, pk):
    """API para obtener detalles de un proveedor (para edición)"""
    from apps.inventory_management.models import Proveedor
    
    try:
        proveedor = get_object_or_404(Proveedor, pk=pk)
        
        data = {
            'success': True,
            'proveedor': {
                'id': str(proveedor.id),
                'nombre_comercial': proveedor.nombre_comercial,
                'razon_social': proveedor.razon_social or '',
                'ruc_nit': proveedor.ruc_nit,
                'direccion': proveedor.direccion or '',
                'telefono': proveedor.telefono or '',
                'email': proveedor.email or '',
                'dias_credito': proveedor.dias_credito,
                'limite_credito': str(proveedor.limite_credito),
                'activo': proveedor.activo,
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

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
    """Historial de ventas con datos reales"""
    from apps.sales_management.models import Venta, Cliente
    from apps.authentication.models import Usuario
    from django.db.models import Q, Sum, Count
    from django.core.paginator import Paginator
    from decimal import Decimal
    
    ventas = Venta.objects.select_related('cliente', 'vendedor').all().order_by('-fecha_venta')
    
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    estado = request.GET.get('estado', '')
    tipo_venta = request.GET.get('tipo_venta', '')
    vendedor_id = request.GET.get('vendedor', '')
    cliente_id = request.GET.get('cliente', '')
    
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)
    
    if estado:
        ventas = ventas.filter(estado=estado)
    
    if tipo_venta:
        ventas = ventas.filter(tipo_venta=tipo_venta)
    
    if vendedor_id:
        ventas = ventas.filter(vendedor_id=vendedor_id)
    
    if cliente_id:
        ventas = ventas.filter(cliente_id=cliente_id)
    
    # Estadísticas
    stats = ventas.filter(estado='COMPLETADA').aggregate(
        total=Sum('total'),
        cantidad=Count('id')
    )
    
    total_ventas = stats['total'] or Decimal('0')
    count_ventas = stats['cantidad'] or 0
    
    # Ventas de HOY
    hoy = timezone.now().date()
    ventas_hoy = Venta.objects.filter(
        fecha_venta__date=hoy,
        estado='COMPLETADA'
    ).count()
    
    # Ventas del MES actual
    inicio_mes = timezone.now().replace(day=1).date()
    ventas_mes = Venta.objects.filter(
        fecha_venta__date__gte=inicio_mes,
        estado='COMPLETADA'
    ).count()
    
    # Paginación
    paginator = Paginator(ventas, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Datos para formulario
    vendedores = Usuario.objects.filter(
        rol__codigo__in=['VENDEDOR', 'ADMIN', 'SUPERVISOR']
    ).order_by('nombres')
    
    clientes = Cliente.objects.filter(activo=True).order_by('apellidos', 'nombres')[:100]
    
    context = {
        'ventas': page_obj,
        'page_obj': page_obj,
        'total_ventas': total_ventas,
        'count_ventas': count_ventas,
        'ventas_hoy': ventas_hoy,
        'ventas_mes': ventas_mes,
        'vendedores': vendedores,
        'clientes': clientes,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado_selected': estado,
        'tipo_venta_selected': tipo_venta,
        'vendedor_selected': vendedor_id,
        'cliente_selected': cliente_id,
        'estados': [
            ('', 'Todos'),
            ('PENDIENTE', 'Pendiente'),
            ('COMPLETADA', 'Completada'),
            ('ANULADA', 'Anulada'),
        ],
        'tipos_venta': [
            ('', 'Todos'),
            ('CONTADO', 'Contado'),
            ('CREDITO', 'Crédito'),
        ],
    }
    
    return render(request, 'custom_admin/ventas/list.html', context)


@ensure_csrf_cookie
@auth_required
def venta_detail_view(request, pk):
    """Detalle de venta con datos reales"""
    from apps.sales_management.models import Venta
    
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'vendedor', 'caja'), pk=pk)
    detalles = venta.detalles.select_related('producto', 'quintal', 'unidad_medida').all()
    pagos = venta.pagos.select_related('usuario').all()
    devoluciones = venta.devoluciones.select_related('usuario_solicita', 'usuario_aprueba').all()
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'pagos': pagos,
        'devoluciones': devoluciones,
    }
    
    return render(request, 'custom_admin/ventas/detail.html', context)


@ensure_csrf_cookie
@auth_required
def venta_anular_view(request, pk):
    """Anular una venta"""
    from apps.sales_management.models import Venta
    from apps.authentication.models import Usuario
    
    if request.method == 'POST':
        try:
            venta = get_object_or_404(Venta, pk=pk)
            
            if venta.estado == 'ANULADA':
                messages.error(request, '❌ La venta ya está anulada.')
                return redirect('custom_admin:venta_detail', pk=pk)
            
            if venta.monto_pagado > 0:
                messages.error(request, '❌ No se puede anular una venta con pagos registrados.')
                return redirect('custom_admin:venta_detail', pk=pk)
            
            from apps.sales_management.services.pos_service import POSService
            usuario = Usuario.objects.filter(rol__codigo='ADMIN').first()
            
            if not usuario:
                usuario = Usuario.objects.first()
            
            POSService.anular_venta(venta, usuario)
            
            messages.success(request, f'✅ Venta {venta.numero_venta} anulada exitosamente.')
            
        except Exception as e:
            messages.error(request, f'❌ Error al anular venta: {str(e)}')
    
    return redirect('custom_admin:ventas_list')


@ensure_csrf_cookie
@auth_required
def venta_ticket_view(request, pk):
    """Imprimir ticket de venta"""
    from apps.sales_management.models import Venta
    from django.http import HttpResponse
    
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'vendedor'), pk=pk)
    detalles = venta.detalles.select_related('producto', 'unidad_medida').all()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Ticket - {venta.numero_venta}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Courier New', monospace;
                width: 80mm;
                margin: 0 auto;
                padding: 10px;
                font-size: 12px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 15px;
                border-bottom: 2px dashed #000;
                padding-bottom: 10px;
            }}
            .header h1 {{ font-size: 18px; margin-bottom: 5px; }}
            .header p {{ font-size: 10px; margin: 2px 0; }}
            .info {{
                margin-bottom: 15px;
                border-bottom: 1px dashed #000;
                padding-bottom: 10px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                margin: 3px 0;
            }}
            .items {{ margin-bottom: 15px; }}
            .item {{
                margin: 5px 0;
                padding: 5px 0;
                border-bottom: 1px dotted #ccc;
            }}
            .item-name {{
                font-weight: bold;
                margin-bottom: 3px;
            }}
            .item-details {{
                display: flex;
                justify-content: space-between;
                font-size: 11px;
            }}
            .totals {{
                border-top: 2px solid #000;
                padding-top: 10px;
                margin-top: 10px;
            }}
            .total-row {{
                display: flex;
                justify-content: space-between;
                margin: 3px 0;
            }}
            .total-row.final {{
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
                padding-top: 10px;
                border-top: 2px dashed #000;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                padding-top: 10px;
                border-top: 2px dashed #000;
                font-size: 10px;
            }}
            @media print {{ body {{ width: 80mm; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛒 CommerceBox</h1>
            <p>Sistema de Gestión</p>
            <p>──────────────────</p>
        </div>
        
        <div class="info">
            <div class="info-row">
                <span><strong>N° Venta:</strong></span>
                <span>{venta.numero_venta}</span>
            </div>
            <div class="info-row">
                <span><strong>Fecha:</strong></span>
                <span>{venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}</span>
            </div>
            <div class="info-row">
                <span><strong>Vendedor:</strong></span>
                <span>{venta.vendedor.get_full_name()}</span>
            </div>
            {"" if not venta.cliente else f'''
            <div class="info-row">
                <span><strong>Cliente:</strong></span>
                <span>{venta.cliente.nombres} {venta.cliente.apellidos}</span>
            </div>
            <div class="info-row">
                <span><strong>Documento:</strong></span>
                <span>{venta.cliente.numero_documento}</span>
            </div>
            '''}
            <div class="info-row">
                <span><strong>Tipo:</strong></span>
                <span>{venta.get_tipo_venta_display()}</span>
            </div>
        </div>
        
        <div class="items">
            <h3 style="margin-bottom: 10px;">PRODUCTOS</h3>
    """
    
    for detalle in detalles:
        if detalle.cantidad_unidades:
            cantidad = f"{detalle.cantidad_unidades} und"
            precio = f"${float(detalle.precio_unitario):,.2f}"
        else:
            cantidad = f"{float(detalle.peso_vendido):,.3f} {detalle.unidad_medida.abreviatura if detalle.unidad_medida else 'kg'}"
            precio = f"${float(detalle.precio_por_unidad_peso):,.2f}/{detalle.unidad_medida.abreviatura if detalle.unidad_medida else 'kg'}"
        
        html += f"""
            <div class="item">
                <div class="item-name">{detalle.producto.nombre}</div>
                <div class="item-details">
                    <span>{cantidad} × {precio}</span>
                    <span>${float(detalle.total):,.2f}</span>
                </div>
            </div>
        """
    
    html += f"""
        </div>
        
        <div class="totals">
            <div class="total-row">
                <span>Subtotal:</span>
                <span>${float(venta.subtotal):,.2f}</span>
            </div>
            {"" if venta.descuento == 0 else f'''
            <div class="total-row">
                <span>Descuento:</span>
                <span>-${float(venta.descuento):,.2f}</span>
            </div>
            '''}
            {"" if venta.impuestos == 0 else f'''
            <div class="total-row">
                <span>Impuestos:</span>
                <span>${float(venta.impuestos):,.2f}</span>
            </div>
            '''}
            <div class="total-row final">
                <span>TOTAL:</span>
                <span>${float(venta.total):,.2f}</span>
            </div>
            {"" if venta.tipo_venta != 'CONTADO' else f'''
            <div class="total-row">
                <span>Pagado:</span>
                <span>${float(venta.monto_pagado):,.2f}</span>
            </div>
            <div class="total-row">
                <span>Cambio:</span>
                <span>${float(venta.cambio):,.2f}</span>
            </div>
            '''}
        </div>
        
        <div class="footer">
            <p>¡Gracias por su compra!</p>
            <p>──────────────────</p>
            <p>Este documento no tiene validez fiscal</p>
        </div>
        
        <script>
            window.onload = function() {{
                window.print();
            }};
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html, content_type='text/html')


@ensure_csrf_cookie
@auth_required
def venta_factura_view(request, pk):
    """Generar factura de venta"""
    from apps.sales_management.models import Venta
    from django.http import HttpResponse
    
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'vendedor'), pk=pk)
    
    if not venta.cliente:
        messages.error(request, 'No se puede generar factura para ventas sin cliente.')
        return redirect('custom_admin:venta_detail', pk=pk)
    
    detalles = venta.detalles.select_related('producto', 'unidad_medida').all()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Factura - {venta.numero_factura or venta.numero_venta}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Arial', sans-serif;
                padding: 40px;
                color: #333;
            }}
            .factura {{
                max-width: 800px;
                margin: 0 auto;
                border: 2px solid #3b82f6;
                padding: 30px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: start;
                border-bottom: 3px solid #3b82f6;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .logo {{
                font-size: 32px;
                font-weight: bold;
                color: #3b82f6;
            }}
            .factura-info {{
                text-align: right;
            }}
            .factura-numero {{
                font-size: 24px;
                font-weight: bold;
                color: #3b82f6;
                margin-bottom: 5px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin-bottom: 30px;
            }}
            .info-section {{
                background: #f8fafc;
                padding: 15px;
                border-radius: 8px;
            }}
            .info-section h3 {{
                color: #3b82f6;
                margin-bottom: 10px;
                font-size: 14px;
                text-transform: uppercase;
            }}
            .info-section p {{
                margin: 5px 0;
                font-size: 13px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            thead {{
                background: #3b82f6;
                color: white;
            }}
            th {{
                padding: 12px;
                text-align: left;
                font-size: 13px;
                text-transform: uppercase;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e2e8f0;
                font-size: 13px;
            }}
            tbody tr:hover {{
                background: #f8fafc;
            }}
            .text-right {{
                text-align: right;
            }}
            .totals {{
                margin-top: 20px;
                display: flex;
                justify-content: flex-end;
            }}
            .totals-table {{
                width: 300px;
            }}
            .totals-table tr td {{
                padding: 8px 12px;
                border: none;
            }}
            .totals-table tr.total {{
                background: #3b82f6;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #e2e8f0;
                text-align: center;
                color: #64748b;
                font-size: 12px;
            }}
            @media print {{
                body {{ padding: 0; }}
                .factura {{ border: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="factura">
            <div class="header">
                <div>
                    <div class="logo">🛒 CommerceBox</div>
                    <p style="color: #64748b; margin-top: 5px;">Sistema de Gestión Comercial</p>
                </div>
                <div class="factura-info">
                    <div class="factura-numero">FACTURA</div>
                    <p><strong>N°:</strong> {venta.numero_factura or venta.numero_venta}</p>
                    <p><strong>Fecha:</strong> {venta.fecha_venta.strftime('%d/%m/%Y')}</p>
                </div>
            </div>
            
            <div class="info-grid">
                <div class="info-section">
                    <h3>📦 Información del Cliente</h3>
                    <p><strong>Cliente:</strong> {venta.cliente.nombres} {venta.cliente.apellidos}</p>
                    <p><strong>Documento:</strong> {venta.cliente.get_tipo_documento_display()} - {venta.cliente.numero_documento}</p>
                    {"" if not venta.cliente.telefono else f"<p><strong>Teléfono:</strong> {venta.cliente.telefono}</p>"}
                    {"" if not venta.cliente.email else f"<p><strong>Email:</strong> {venta.cliente.email}</p>"}
                    {"" if not venta.cliente.direccion else f"<p><strong>Dirección:</strong> {venta.cliente.direccion}</p>"}
                </div>
                
                <div class="info-section">
                    <h3>💼 Información de la Venta</h3>
                    <p><strong>Vendedor:</strong> {venta.vendedor.get_full_name()}</p>
                    <p><strong>Tipo de Venta:</strong> {venta.get_tipo_venta_display()}</p>
                    <p><strong>Estado:</strong> {venta.get_estado_display()}</p>
                    {"" if venta.tipo_venta != 'CREDITO' else f'''
                    <p><strong>Fecha Vencimiento:</strong> {venta.fecha_vencimiento.strftime('%d/%m/%Y') if venta.fecha_vencimiento else 'N/A'}</p>
                    '''}
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th style="width: 50%;">Producto</th>
                        <th class="text-right">Cantidad</th>
                        <th class="text-right">Precio Unit.</th>
                        <th class="text-right">Descuento</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for detalle in detalles:
        if detalle.cantidad_unidades:
            cantidad = f"{detalle.cantidad_unidades} und"
            precio = f"${float(detalle.precio_unitario):,.2f}"
        else:
            cantidad = f"{float(detalle.peso_vendido):,.3f} {detalle.unidad_medida.abreviatura if detalle.unidad_medida else 'kg'}"
            precio = f"${float(detalle.precio_por_unidad_peso):,.2f}"
        
        html += f"""
                    <tr>
                        <td><strong>{detalle.producto.nombre}</strong></td>
                        <td class="text-right">{cantidad}</td>
                        <td class="text-right">{precio}</td>
                        <td class="text-right">${float(detalle.descuento_monto):,.2f}</td>
                        <td class="text-right"><strong>${float(detalle.total):,.2f}</strong></td>
                    </tr>
        """
    
    html += f"""
                </tbody>
            </table>
            
            <div class="totals">
                <table class="totals-table">
                    <tr>
                        <td>Subtotal:</td>
                        <td class="text-right"><strong>${float(venta.subtotal):,.2f}</strong></td>
                    </tr>
                    {"" if venta.descuento == 0 else f'''
                    <tr>
                        <td>Descuento:</td>
                        <td class="text-right" style="color: #dc2626;"><strong>-${float(venta.descuento):,.2f}</strong></td>
                    </tr>
                    '''}
                    {"" if venta.impuestos == 0 else f'''
                    <tr>
                        <td>Impuestos:</td>
                        <td class="text-right"><strong>${float(venta.impuestos):,.2f}</strong></td>
                    </tr>
                    '''}
                    <tr class="total">
                        <td>TOTAL:</td>
                        <td class="text-right">${float(venta.total):,.2f}</td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                <p>Gracias por su preferencia</p>
                <p style="margin-top: 10px;">Este documento es una representación impresa de una factura electrónica</p>
            </div>
        </div>
        
        <script>
            window.onload = function() {{
                window.print();
            }};
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html, content_type='text/html')


# ========================================
# NUEVAS VISTAS PARA EXPORTACIONES
# ========================================

@ensure_csrf_cookie
def venta_detalle_api(request, pk):
    """API endpoint para obtener detalles de una venta"""
    from apps.sales_management.models import Venta
    
    try:
        venta = get_object_or_404(Venta.objects.select_related('cliente', 'vendedor'), pk=pk)
        
        # Obtener items de la venta
        items = []
        for item in venta.detalles.select_related('producto', 'unidad_medida').all():
            items.append({
                'producto_nombre': item.producto.nombre,
                'codigo_barras': item.producto.codigo_barras or 'Sin código',
                'cantidad': str(item.cantidad_unidades) if item.cantidad_unidades else str(float(item.peso_vendido)),
                'precio_unitario': str(item.precio_unitario) if item.precio_unitario else str(float(item.precio_por_unidad_peso)),
                'descuento': str(item.descuento_monto),
                'subtotal': str(item.subtotal),
                'total': str(item.total),
            })
        
        # Construir respuesta
        data = {
            'success': True,
            'venta': {
                'numero_venta': venta.numero_venta,
                'fecha_venta': venta.fecha_venta.strftime('%d/%m/%Y %H:%M'),
                'estado': venta.get_estado_display(),
                'tipo_venta': venta.get_tipo_venta_display(),
                'vendedor': venta.vendedor.get_full_name(),
                'cliente': f"{venta.cliente.nombres} {venta.cliente.apellidos}" if venta.cliente else None,
                'metodo_pago': venta.get_metodo_pago_display() if hasattr(venta, 'metodo_pago') else 'N/A',
                'subtotal': str(venta.subtotal),
                'descuento': str(venta.descuento),
                'total': str(venta.total),
                'monto_pagado': str(venta.monto_pagado),
                'cambio': str(venta.cambio) if venta.cambio else '0.00',
                'saldo_pendiente': str(venta.saldo_pendiente),
                'items': items,
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@ensure_csrf_cookie
@auth_required
def exportar_venta_excel_individual(request, pk):
    """Exportar una venta individual a Excel"""
    from apps.sales_management.models import Venta
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from io import BytesIO
    
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'vendedor'), pk=pk)
    
    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = f"Venta {venta.numero_venta}"
    
    # Estilos
    header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    title_font = Font(bold=True, size=14)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # TÍTULO
    ws.merge_cells('A1:F1')
    ws['A1'] = f"DETALLE DE VENTA - {venta.numero_venta}"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    
    # INFORMACIÓN GENERAL
    row = 3
    ws[f'A{row}'] = "Fecha:"
    ws[f'B{row}'] = venta.fecha_venta.strftime('%d/%m/%Y %H:%M')
    ws[f'A{row}'].font = Font(bold=True)
    
    row += 1
    ws[f'A{row}'] = "Cliente:"
    ws[f'B{row}'] = f"{venta.cliente.nombres} {venta.cliente.apellidos}" if venta.cliente else "Público General"
    ws[f'A{row}'].font = Font(bold=True)
    
    row += 1
    ws[f'A{row}'] = "Vendedor:"
    ws[f'B{row}'] = venta.vendedor.get_full_name()
    ws[f'A{row}'].font = Font(bold=True)
    
    row += 1
    ws[f'A{row}'] = "Tipo de Venta:"
    ws[f'B{row}'] = venta.get_tipo_venta_display()
    ws[f'A{row}'].font = Font(bold=True)
    
    row += 1
    ws[f'A{row}'] = "Estado:"
    ws[f'B{row}'] = venta.get_estado_display()
    ws[f'A{row}'].font = Font(bold=True)
    
    # PRODUCTOS
    row += 2
    headers = ['Producto', 'Cantidad', 'Precio Unit.', 'Descuento', 'Subtotal', 'Total']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # Items
    for item in venta.detalles.select_related('producto', 'unidad_medida').all():
        row += 1
        ws.cell(row=row, column=1, value=item.producto.nombre).border = border
        
        if item.cantidad_unidades:
            ws.cell(row=row, column=2, value=float(item.cantidad_unidades)).border = border
            ws.cell(row=row, column=3, value=float(item.precio_unitario)).border = border
        else:
            ws.cell(row=row, column=2, value=float(item.peso_vendido)).border = border
            ws.cell(row=row, column=3, value=float(item.precio_por_unidad_peso)).border = border
        
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3).number_format = '$#,##0.00'
        ws.cell(row=row, column=4, value=float(item.descuento_monto)).border = border
        ws.cell(row=row, column=4).number_format = '$#,##0.00'
        ws.cell(row=row, column=5, value=float(item.subtotal)).border = border
        ws.cell(row=row, column=5).number_format = '$#,##0.00'
        ws.cell(row=row, column=6, value=float(item.total)).border = border
        ws.cell(row=row, column=6).number_format = '$#,##0.00'
    
    # TOTALES
    row += 2
    ws.cell(row=row, column=5, value="Subtotal:").font = Font(bold=True)
    ws.cell(row=row, column=6, value=float(venta.subtotal)).number_format = '$#,##0.00'
    
    row += 1
    ws.cell(row=row, column=5, value="Descuento:").font = Font(bold=True)
    ws.cell(row=row, column=6, value=float(venta.descuento)).number_format = '$#,##0.00'
    
    row += 1
    ws.cell(row=row, column=5, value="TOTAL:").font = Font(bold=True, size=14)
    ws.cell(row=row, column=6, value=float(venta.total)).font = Font(bold=True, size=14)
    ws.cell(row=row, column=6).number_format = '$#,##0.00'
    
    # Ajustar anchos
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    
    # Preparar respuesta
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=venta_{venta.numero_venta}.xlsx'
    
    return response


@ensure_csrf_cookie
@auth_required
def exportar_venta_pdf_individual(request, pk):
    """Exportar una venta individual a PDF"""
    from apps.sales_management.models import Venta
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO
    
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'vendedor'), pk=pk)
    
    # Crear buffer
    buffer = BytesIO()
    
    # Crear documento
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=30,
        alignment=1  # Centro
    )
    
    # TÍTULO
    title = Paragraph(f"DETALLE DE VENTA - {venta.numero_venta}", title_style)
    elements.append(title)
    
    # INFORMACIÓN GENERAL
    info_data = [
        ['Fecha:', venta.fecha_venta.strftime('%d/%m/%Y %H:%M')],
        ['Cliente:', f"{venta.cliente.nombres} {venta.cliente.apellidos}" if venta.cliente else "Público General"],
        ['Vendedor:', venta.vendedor.get_full_name()],
        ['Tipo de Venta:', venta.get_tipo_venta_display()],
        ['Estado:', venta.get_estado_display()],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # PRODUCTOS
    productos_header = Paragraph('<b>PRODUCTOS</b>', styles['Heading2'])
    elements.append(productos_header)
    elements.append(Spacer(1, 10))
    
    # Tabla de productos
    productos_data = [['Producto', 'Cant.', 'Precio Unit.', 'Desc.', 'Subtotal', 'Total']]
    
    for item in venta.detalles.select_related('producto', 'unidad_medida').all():
        if item.cantidad_unidades:
            cantidad = str(item.cantidad_unidades)
            precio = f"${item.precio_unitario:.2f}"
        else:
            cantidad = f"{float(item.peso_vendido):.3f}"
            precio = f"${item.precio_por_unidad_peso:.2f}"
        
        productos_data.append([
            item.producto.nombre,
            cantidad,
            precio,
            f"${item.descuento_monto:.2f}",
            f"${item.subtotal:.2f}",
            f"${item.total:.2f}",
        ])
    
    productos_table = Table(productos_data, colWidths=[2.5*inch, 0.7*inch, 1*inch, 0.9*inch, 1*inch, 1*inch])
    productos_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Body
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    elements.append(productos_table)
    elements.append(Spacer(1, 20))
    
    # TOTALES
    totales_data = [
        ['Subtotal:', f"${venta.subtotal:.2f}"],
        ['Descuento:', f"${venta.descuento:.2f}"],
        ['', ''],
        ['TOTAL:', f"${venta.total:.2f}"],
    ]
    
    totales_table = Table(totales_data, colWidths=[4.5*inch, 1.5*inch])
    totales_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, 1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, 1), 'Helvetica', 10),
        ('FONT', (0, 3), (-1, 3), 'Helvetica-Bold', 14),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, 3), (-1, 3), 2, colors.HexColor('#3B82F6')),
        ('TOPPADDING', (0, 3), (-1, 3), 10),
    ]))
    elements.append(totales_table)
    
    # Construir PDF
    doc.build(elements)
    
    # Preparar respuesta
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=venta_{venta.numero_venta}.pdf'
    
    return response


@ensure_csrf_cookie
@auth_required
def exportar_ventas_excel_general(request):
    """Exportar todas las ventas filtradas a Excel"""
    from apps.sales_management.models import Venta
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from datetime import datetime
    from io import BytesIO
    
    # Obtener filtros de la URL
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    tipo_venta = request.GET.get('tipo_venta')
    vendedor_id = request.GET.get('vendedor')
    cliente_id = request.GET.get('cliente')
    
    # Filtrar ventas
    ventas = Venta.objects.select_related('cliente', 'vendedor').all().order_by('-fecha_venta')
    
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)
    if estado:
        ventas = ventas.filter(estado=estado)
    if tipo_venta:
        ventas = ventas.filter(tipo_venta=tipo_venta)
    if vendedor_id:
        ventas = ventas.filter(vendedor_id=vendedor_id)
    if cliente_id:
        ventas = ventas.filter(cliente_id=cliente_id)
    
    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"
    
    # Estilos
    header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, size=14)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # TÍTULO
    ws.merge_cells('A1:J1')
    ws['A1'] = f"REPORTE DE VENTAS - {datetime.now().strftime('%d/%m/%Y')}"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    
    # HEADERS
    headers = ['N° Venta', 'Fecha', 'Cliente', 'Vendedor', 'Tipo', 'Estado', 
               'Subtotal', 'Descuento', 'Total', 'Pagado']
    
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # DATOS
    row = 4
    for venta in ventas:
        ws.cell(row=row, column=1, value=venta.numero_venta).border = border
        ws.cell(row=row, column=2, value=venta.fecha_venta.strftime('%d/%m/%Y %H:%M')).border = border
        ws.cell(row=row, column=3, value=f"{venta.cliente.nombres} {venta.cliente.apellidos}" if venta.cliente else "Público General").border = border
        ws.cell(row=row, column=4, value=venta.vendedor.get_full_name()).border = border
        ws.cell(row=row, column=5, value=venta.get_tipo_venta_display()).border = border
        ws.cell(row=row, column=6, value=venta.get_estado_display()).border = border
        
        ws.cell(row=row, column=7, value=float(venta.subtotal)).border = border
        ws.cell(row=row, column=7).number_format = '$#,##0.00'
        
        ws.cell(row=row, column=8, value=float(venta.descuento)).border = border
        ws.cell(row=row, column=8).number_format = '$#,##0.00'
        
        ws.cell(row=row, column=9, value=float(venta.total)).border = border
        ws.cell(row=row, column=9).number_format = '$#,##0.00'
        
        ws.cell(row=row, column=10, value=float(venta.monto_pagado)).border = border
        ws.cell(row=row, column=10).number_format = '$#,##0.00'
        
        row += 1
    
    # TOTALES
    row += 1
    ws.cell(row=row, column=8, value="TOTALES:").font = Font(bold=True)
    
    total_ventas = sum(float(v.total) for v in ventas)
    ws.cell(row=row, column=9, value=total_ventas).font = Font(bold=True)
    ws.cell(row=row, column=9).number_format = '$#,##0.00'
    
    total_pagado = sum(float(v.monto_pagado) for v in ventas)
    ws.cell(row=row, column=10, value=total_pagado).font = Font(bold=True)
    ws.cell(row=row, column=10).number_format = '$#,##0.00'
    
    # Ajustar anchos
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 12
    ws.column_dimensions['J'].width = 12
    
    # Preparar respuesta
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


@ensure_csrf_cookie
@auth_required
def exportar_ventas_pdf_general(request):
    """Exportar todas las ventas filtradas a PDF"""
    from apps.sales_management.models import Venta
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    from datetime import datetime
    
    # Obtener filtros (mismo código que Excel)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    tipo_venta = request.GET.get('tipo_venta')
    vendedor_id = request.GET.get('vendedor')
    cliente_id = request.GET.get('cliente')
    
    # Filtrar ventas
    ventas = Venta.objects.select_related('cliente', 'vendedor').all().order_by('-fecha_venta')
    
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)
    if estado:
        ventas = ventas.filter(estado=estado)
    if tipo_venta:
        ventas = ventas.filter(tipo_venta=tipo_venta)
    if vendedor_id:
        ventas = ventas.filter(vendedor_id=vendedor_id)
    if cliente_id:
        ventas = ventas.filter(cliente_id=cliente_id)
    
    # Crear buffer
    buffer = BytesIO()
    
    # Crear documento (landscape para más espacio)
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    title = Paragraph(f"REPORTE DE VENTAS - {datetime.now().strftime('%d/%m/%Y')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10))
    
    # Tabla de ventas
    data = [['N° Venta', 'Fecha', 'Cliente', 'Tipo', 'Total', 'Estado']]
    
    for venta in ventas:
        data.append([
            venta.numero_venta,
            venta.fecha_venta.strftime('%d/%m/%Y'),
            (f"{venta.cliente.nombres} {venta.cliente.apellidos}" if venta.cliente else "Público")[:20],
            venta.get_tipo_venta_display(),
            f"${venta.total:.2f}",
            venta.get_estado_display(),
        ])
    
    # Totales
    total = sum(float(v.total) for v in ventas)
    data.append(['', '', '', 'TOTAL:', f"${total:.2f}", ''])
    
    table = Table(data, colWidths=[1.2*inch, 1.1*inch, 1.8*inch, 1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Body
        ('FONT', (0, 1), (-1, -2), 'Helvetica', 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        
        # Total row
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 10),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#3B82F6')),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    
    # Preparar respuesta
    buffer.seek(0)
    filename = f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


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


@ensure_csrf_cookie
@auth_required
def ventas_export_excel(request):
    """Exportar ventas a Excel - FUNCIÓN ANTIGUA (mantener por compatibilidad)"""
    return exportar_ventas_excel_general(request)


@ensure_csrf_cookie
@auth_required
def ventas_export_pdf(request):
    """Exportar ventas a PDF - FUNCIÓN ANTIGUA (mantener por compatibilidad)"""
    return exportar_ventas_pdf_general(request)


# ========================================
# PUNTO DE VENTA (POS)
# ========================================

@ensure_csrf_cookie
@auth_required
def pos_view(request):
    """Punto de Venta principal"""
    from apps.sales_management.models import Cliente
    from apps.inventory_management.models import Categoria
    
    clientes = Cliente.objects.filter(activo=True).order_by('apellidos', 'nombres')
    categorias = Categoria.objects.filter(activa=True).order_by('nombre')
    
    context = {
        'clientes': clientes,
        'categorias': categorias,
    }
    
    return render(request, 'custom_admin/pos/punto_venta.html', context)


def api_buscar_productos(request):
    """API para buscar productos"""
    from apps.inventory_management.models import Producto, ProductoNormal, Quintal
    from django.db.models import Q, Sum
    from django.http import JsonResponse
    
    query = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '')
    cargar_todos = request.GET.get('all', '') == 'true'
    
    if not query and not categoria_id and not cargar_todos:
        return JsonResponse({'productos': []})
    
    productos = Producto.objects.select_related('categoria', 'unidad_medida_base').filter(activo=True)
    
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(codigo_barras__icontains=query) |
            Q(descripcion__icontains=query)
        )
    
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    
    if not cargar_todos:
        productos = productos[:20]
    else:
        productos = productos[:100]
    
    data = []
    for p in productos:
        # Obtener stock según tipo de inventario
        stock_actual = 0
        
        if p.tipo_inventario == 'NORMAL':
            try:
                inventario = p.inventario_normal
                stock_actual = float(inventario.stock_actual) if inventario else 0
            except ProductoNormal.DoesNotExist:
                stock_actual = 0
        elif p.tipo_inventario == 'QUINTAL':
            # Sumar el peso actual de todos los quintales disponibles
            stock_actual = float(
                Quintal.objects.filter(
                    producto=p,
                    estado='DISPONIBLE'
                ).aggregate(
                    total=Sum('peso_actual')
                )['total'] or 0
            )
        
        data.append({
            'id': str(p.id),
            'nombre': p.nombre,
            'codigo_barras': p.codigo_barras or '',
            'categoria': p.categoria.nombre if p.categoria else '',
            'tipo_inventario': p.tipo_inventario,
            'precio_unitario': float(p.precio_unitario) if p.precio_unitario else 0,
            'precio_por_unidad_peso': float(p.precio_por_unidad_peso) if p.precio_por_unidad_peso else 0,
            'stock_actual': stock_actual,
            'unidad_medida': p.unidad_medida_base.abreviatura if p.unidad_medida_base else 'und',
        })
    
    return JsonResponse({'productos': data})


@ensure_csrf_cookie
def api_obtener_producto(request, producto_id):
    """API para obtener info completa de un producto"""
    from apps.inventory_management.models import Producto
    from django.http import JsonResponse
    
    producto = get_object_or_404(Producto.objects.select_related('categoria', 'unidad_medida_base'), pk=producto_id)
    
    data = {
        'id': str(producto.id),
        'nombre': producto.nombre,
        'descripcion': producto.descripcion or '',
        'codigo_barras': producto.codigo_barras or '',
        'categoria': producto.categoria.nombre if producto.categoria else '',
        'tipo_inventario': producto.tipo_inventario,
        'precio_unitario': float(producto.precio_unitario) if producto.precio_unitario else 0,
        'precio_por_unidad_peso': float(producto.precio_por_unidad_peso) if producto.precio_por_unidad_peso else 0,
        'stock_actual': float(producto.stock_actual) if hasattr(producto, 'stock_actual') else 0,
        'unidad_medida': producto.unidad_medida_base.abreviatura if producto.unidad_medida_base else 'und',
        'permite_descuento': True,
        'descuento_maximo': float(producto.categoria.descuento_maximo_permitido) if producto.categoria else 10.0,
    }
    
    return JsonResponse(data)


@ensure_csrf_cookie
def api_procesar_venta(request):
    """API para procesar y guardar la venta"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    import json
    from django.http import JsonResponse
    from apps.sales_management.models import Venta, DetalleVenta, Cliente, Pago
    from apps.inventory_management.models import Producto
    from apps.authentication.models import Usuario
    from decimal import Decimal
    from django.utils import timezone
    from django.db import transaction
    
    try:
        data = json.loads(request.body)
        
        items = data.get('items', [])
        if not items:
            return JsonResponse({'success': False, 'error': 'No hay productos en el carrito'})
        
        cliente_id = data.get('cliente_id')
        tipo_venta = data.get('tipo_venta', 'CONTADO')
        metodo_pago = data.get('metodo_pago', 'EFECTIVO')
        
        try:
            monto_recibido = Decimal(str(data.get('monto_recibido', '0')))
        except:
            monto_recibido = Decimal('0')
        
        usuario = Usuario.objects.filter(rol__codigo__in=['VENDEDOR', 'ADMIN', 'CAJERO']).first()
        if not usuario:
            usuario = Usuario.objects.first()
        
        if not usuario:
            return JsonResponse({'success': False, 'error': 'No hay usuarios en el sistema'})
        
        cliente = None
        if cliente_id:
            try:
                cliente = Cliente.objects.get(id=cliente_id)
            except Cliente.DoesNotExist:
                pass
        
        subtotal = Decimal('0')
        descuento_total = Decimal('0')
        
        for item in items:
            print(f"DEBUG: Item recibido = {item}")
            try:
                item_subtotal = Decimal(str(item.get('subtotal', '0')))
                item_descuento = Decimal(str(item.get('descuento', '0')))
                subtotal += item_subtotal
                descuento_total += item_descuento
            except:
                continue
        
        total = subtotal - descuento_total
        
        with transaction.atomic():
            # ✅ GENERAR NÚMERO DE VENTA AQUÍ - MÉTODO ULTRA ROBUSTO
            año = timezone.now().year
            
            # Método 1: Contar ventas del año
            ventas_año = Venta.objects.filter(
                numero_venta__startswith=f'VNT-{año}-'
            ).count()
            
            # Siguiente número
            siguiente = ventas_año + 1
            
            # Generar con formato
            numero_venta_generado = 'VNT-{}-{:05d}'.format(año, siguiente)
            
            # ✅ CREAR VENTA CON NÚMERO EXPLÍCITO
            venta = Venta.objects.create(
                numero_venta=numero_venta_generado,  # ✅ Pasamos el número YA generado
                cliente=cliente,
                vendedor=usuario,
                tipo_venta=tipo_venta,
                subtotal=subtotal,
                descuento=descuento_total,
                impuestos=Decimal('0'),
                total=total,
                estado='PENDIENTE',
                monto_pagado=Decimal('0'),
                cambio=Decimal('0'),
            )
            
            # Crear detalles
            orden = 1
            for item in items:
                print(f"DEBUG: Item recibido = {item}")
                try:
                    producto = Producto.objects.get(id=item['producto_id'])
                    
                    cantidad = Decimal(str(item.get('cantidad', '0')))
                    precio = Decimal(str(item.get('precio', '0')))
                    descuento = Decimal(str(item.get('descuento', '0')))
                    descuento_porcentaje = Decimal(str(item.get('descuento_porcentaje', '0')))
                    
                    costo_unitario = precio * Decimal('0.7')
                    costo_total = cantidad * costo_unitario
                    item_subtotal = cantidad * precio
                    item_total = item_subtotal - descuento
                    
                    detalle_data = {
                        'venta': venta,
                        'producto': producto,
                        'orden': orden,
                        'costo_unitario': costo_unitario,
                        'costo_total': costo_total,
                        'descuento_porcentaje': descuento_porcentaje,
                        'descuento_monto': descuento,
                        'subtotal': item_subtotal,
                        'total': item_total,
                    }
                    
                    # Manejar quintales si es una venta de quintal
                    if item.get('es_quintal') and item.get('quintal_id'):
                        from apps.inventory_management.models import Quintal
                        try:
                            quintal = Quintal.objects.get(id=item['quintal_id'])
                            detalle_data['quintal'] = quintal
                            detalle_data['peso_vendido'] = Decimal(str(item.get('peso_vendido', 0)))
                            detalle_data['precio_por_unidad_peso'] = producto.precio_por_unidad_peso
                            detalle_data['unidad_medida'] = quintal.unidad_medida
                            print(f"DEBUG: Quintal {quintal.codigo_unico} agregado")
                        except Quintal.DoesNotExist:
                            print(f"ERROR: Quintal no encontrado")
                    elif producto.tipo_inventario == 'QUINTAL':
                        # Quintal sin datos específicos
                        detalle_data['peso_vendido'] = cantidad
                        detalle_data['precio_por_unidad_peso'] = precio
                    else:
                        # Producto normal
                        detalle_data['cantidad_unidades'] = int(cantidad)
                        detalle_data['precio_unitario'] = precio
                    
                    print(f"DEBUG: Creando DetalleVenta con data: {detalle_data}")
                    detalle = DetalleVenta.objects.create(**detalle_data)
                    print(f"DEBUG: DetalleVenta creado ID={detalle.id}")
                    
                    if detalle.quintal:
                        print(f"DEBUG: quintal={detalle.quintal.codigo_unico}")
                        print(f"DEBUG: peso_vendido={detalle.peso_vendido}")
                    
                    orden += 1
                    
                except Producto.DoesNotExist:
                    print(f"ERROR: Producto {item.get('producto_id')} no encontrado")
                    continue
                except Exception as e:
                    import traceback
                    print(f"ERROR en detalle: {e}")
                    print("TRACEBACK COMPLETO:")
                    traceback.print_exc()
                    continue
            
        return JsonResponse({
            'success': True,
            'venta_id': str(venta.id),
            'numero_venta': venta.numero_venta,
            'total': float(total),
            'cambio': float(venta.cambio),
        })
        
    except Exception as e:
        import traceback
        error_completo = traceback.format_exc()
        print("=" * 80)
        print("ERROR COMPLETO:")
        print(error_completo)
        print("=" * 80)
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)


@ensure_csrf_cookie
def api_venta_detalle(request, venta_id):
    """API para obtener detalle de una venta"""
    from apps.sales_management.models import Venta
    from django.http import JsonResponse
    
    venta = get_object_or_404(
        Venta.objects.select_related('cliente', 'vendedor'), 
        pk=venta_id
    )
    
    detalles = venta.detalles.select_related('producto', 'unidad_medida').all()
    pagos = venta.pagos.select_related('usuario').all()
    
    venta_data = {
        'numero_venta': venta.numero_venta,
        'fecha_venta': venta.fecha_venta.strftime('%d/%m/%Y %H:%M'),
        'estado': venta.estado,
        'tipo_venta': venta.get_tipo_venta_display(),
        'subtotal': float(venta.subtotal),
        'descuento': float(venta.descuento),
        'impuestos': float(venta.impuestos),
        'total': float(venta.total),
        'monto_pagado': float(venta.monto_pagado),
        'cliente_nombre': f"{venta.cliente.nombres} {venta.cliente.apellidos}" if venta.cliente else None,
        'cliente_documento': venta.cliente.numero_documento if venta.cliente else None,
        'cliente_telefono': venta.cliente.telefono if venta.cliente else None,
        'vendedor_nombre': venta.vendedor.get_full_name(),
    }
    
    detalles_data = []
    for detalle in detalles:
        detalles_data.append({
            'producto_nombre': detalle.producto.nombre,
            'cantidad_unidades': detalle.cantidad_unidades,
            'peso_vendido': float(detalle.peso_vendido) if detalle.peso_vendido else None,
            'unidad_medida': detalle.unidad_medida.abreviatura if detalle.unidad_medida else 'und',
            'precio_unitario': float(detalle.precio_unitario) if detalle.precio_unitario else None,
            'precio_por_unidad_peso': float(detalle.precio_por_unidad_peso) if detalle.precio_por_unidad_peso else None,
            'descuento_monto': float(detalle.descuento_monto),
            'total': float(detalle.total),
        })
    
    pagos_data = []
    for pago in pagos:
        pagos_data.append({
            'forma_pago': pago.get_forma_pago_display(),
            'monto': float(pago.monto),
            'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y %H:%M'),
            'usuario': pago.usuario.get_full_name(),
        })
    
    return JsonResponse({
        'venta': venta_data,
        'detalles': detalles_data,
        'pagos': pagos_data,
    })

# ========================================
# ENTRADA DE INVENTARIO UNIFICADA
# ========================================

from apps.system_configuration.models import ConfiguracionSistema

@ensure_csrf_cookie
@auth_required
def entrada_inventario_view(request):
    from apps.inventory_management.models import Proveedor, UnidadMedida, Categoria, Marca
    
    categorias = Categoria.objects.filter(activa=True).order_by('orden', 'nombre')
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre_comercial')
    marcas = Marca.objects.filter(activa=True).order_by('nombre')
    unidades_medida = UnidadMedida.objects.filter(activa=True).order_by('orden_display')
    
    # ✅ OBTENER IVA DESDE CONFIGURACIÓN
    config = ConfiguracionSistema.get_config()
    iva_default = float(config.iva_default)
    
    context = {
        'categorias': categorias,
        'proveedores': proveedores,
        'marcas': marcas,
        'unidades_medida': unidades_medida,
        'iva_default': iva_default,  # ✅ PASAR IVA AL TEMPLATE
    }
    
    return render(request, 'custom_admin/inventario/entrada_inventario.html', context)
def api_buscar_producto_codigo(request):
    """API para buscar producto por código de barras"""
    from apps.inventory_management.models import Producto
    from django.http import JsonResponse
    
    codigo = request.GET.get('codigo', '').strip()
    
    if not codigo:
        return JsonResponse({
            'success': False,
            'mensaje': 'Código vacío'
        })
    
    try:
        producto = Producto.objects.get(codigo_barras=codigo, activo=True)
        
        data = {
            'success': True,
            'producto': {
                'id': str(producto.id),
                'nombre': producto.nombre,
                'codigo_barras': producto.codigo_barras,
                'tipo_inventario': producto.tipo_inventario,
                'unidad_medida_id': str(producto.unidad_medida_base.id) if producto.unidad_medida_base else None,
            }
        }
        
        return JsonResponse(data)
        
    except Producto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'mensaje': f'Producto no encontrado: {codigo}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }, status=500)


@ensure_csrf_cookie
def api_procesar_entrada_masiva(request):
    """API para procesar entrada masiva de productos"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    import json
    from django.http import JsonResponse
    from django.db import transaction
    from apps.inventory_management.models import (
        Producto, Quintal, ProductoNormal, MovimientoInventario,
        Proveedor, UnidadMedida
    )
    from apps.authentication.models import Usuario
    from decimal import Decimal
    from django.utils import timezone
    
    try:
        data = json.loads(request.body)
        entradas = data.get('entradas', [])
        numero_factura = data.get('numero_factura', '')
        observaciones = data.get('observaciones', '')
        
        if not entradas:
            return JsonResponse({'success': False, 'error': 'No hay productos para procesar'})
        
        usuario = Usuario.objects.filter(rol__codigo__in=['ADMIN', 'SUPERVISOR']).first()
        if not usuario:
            usuario = Usuario.objects.first()
        
        codigos_generados = []
        quintales_creados = 0
        productos_actualizados = 0
        
        with transaction.atomic():
            for entrada in entradas:
                try:
                    producto = Producto.objects.get(id=entrada['producto_id'])
                    proveedor = Proveedor.objects.get(id=entrada['proveedor_id'])
                    
                    if producto.tipo_inventario == 'QUINTAL':
                        # Crear Quintal
                        from apps.inventory_management.utils.barcode_generator import BarcodeGenerator
                        
                        unidad_medida = UnidadMedida.objects.get(id=entrada['unidad_medida_id'])
                        peso_inicial = Decimal(str(entrada['peso_inicial']))
                        costo_total = Decimal(str(entrada['costo_total']))
                        
                        quintal = Quintal.objects.create(
                            codigo_unico=BarcodeGenerator.generar_codigo_quintal(producto),
                            producto=producto,
                            proveedor=proveedor,
                            peso_inicial=peso_inicial,
                            peso_actual=peso_inicial,
                            unidad_medida=unidad_medida,
                            costo_total=costo_total,
                            costo_por_unidad=costo_total / peso_inicial,
                            fecha_recepcion=timezone.now(),
                            fecha_vencimiento=entrada.get('fecha_vencimiento') or None,
                            lote_proveedor=entrada.get('lote_proveedor', ''),
                            numero_factura_compra=numero_factura,
                            usuario_registro=usuario,
                            estado='DISPONIBLE'
                        )
                        
                        quintales_creados += 1
                        
                        # Generar códigos de barras
                        cantidad_etiquetas = int(peso_inicial)  # 1 etiqueta por unidad de peso
                        
                        codigos_generados.append({
                            'tipo': 'QUINTAL',
                            'codigo': quintal.codigo_unico,
                            'producto_nombre': producto.nombre,
                            'cantidad_etiquetas': cantidad_etiquetas,
                            'peso_unitario': 1,  # 1 lb/kg por etiqueta
                            'unidad': unidad_medida.abreviatura,
                            'pdf_url': f'/panel/api/inventario/generar-pdf-codigos/?quintal_id={quintal.id}'
                        })
                        
                    else:
                        # Producto Normal
                        cantidad = int(entrada['cantidad_unidades'])
                        costo_unitario = Decimal(str(entrada['costo_unitario']))
                        
                        producto_normal, created = ProductoNormal.objects.get_or_create(
                            producto=producto,
                            defaults={
                                'stock_actual': 0,
                                'stock_minimo': 10,
                                'costo_unitario': costo_unitario
                            }
                        )
                        
                        stock_antes = producto_normal.stock_actual
                        producto_normal.stock_actual += cantidad
                        
                        # Actualizar costo promedio ponderado
                        if stock_antes > 0:
                            costo_total_anterior = stock_antes * producto_normal.costo_unitario
                            costo_total_nuevo = cantidad * costo_unitario
                            stock_total = stock_antes + cantidad
                            producto_normal.costo_unitario = (costo_total_anterior + costo_total_nuevo) / stock_total
                        else:
                            producto_normal.costo_unitario = costo_unitario
                        
                        producto_normal.fecha_ultima_entrada = timezone.now()
                        producto_normal.lote = entrada.get('lote', '')
                        producto_normal.fecha_vencimiento = entrada.get('fecha_vencimiento') or None
                        producto_normal.save()
                        
                        # Registrar movimiento
                        MovimientoInventario.objects.create(
                            producto_normal=producto_normal,
                            tipo_movimiento='ENTRADA_COMPRA',
                            cantidad=cantidad,
                            stock_antes=stock_antes,
                            stock_despues=producto_normal.stock_actual,
                            costo_unitario=costo_unitario,
                            costo_total=cantidad * costo_unitario,
                            usuario=usuario,
                            observaciones=observaciones or f"Entrada masiva - Factura: {numero_factura}"
                        )
                        
                        productos_actualizados += 1
                        
                        # Generar códigos de barras
                        codigos_generados.append({
                            'tipo': 'NORMAL',
                            'codigo': producto.codigo_barras,
                            'producto_nombre': producto.nombre,
                            'cantidad_etiquetas': cantidad,
                            'pdf_url': f'/panel/api/inventario/generar-pdf-codigos/?producto_id={producto.id}&cantidad={cantidad}'
                        })
                        
                except Exception as e:
                    print(f"Error procesando entrada: {e}")
                    continue
        
        return JsonResponse({
            'success': True,
            'quintales_creados': quintales_creados,
            'productos_actualizados': productos_actualizados,
            'codigos_generados': codigos_generados,
            'mensaje': f'Entrada procesada: {quintales_creados} quintales, {productos_actualizados} productos actualizados'
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)

@ensure_csrf_cookie
def api_generar_pdf_codigos(request):
    """Genera y devuelve PDF con códigos de barras - VERSIÓN ORGANIZADA"""
    from django.http import HttpResponse, JsonResponse
    from apps.inventory_management.models import Quintal, Producto
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.graphics.barcode import code128
    from io import BytesIO
    from datetime import datetime
    
    quintal_id = request.GET.get('quintal_id')
    producto_id = request.GET.get('producto_id')
    cantidad = int(request.GET.get('cantidad', 50))
    
    try:
        # ========================================
        # CONFIGURACIÓN OPTIMIZADA PARA ETIQUETAS
        # ========================================
        ETIQUETAS_POR_FILA = 3
        ETIQUETAS_POR_COLUMNA = 8
        ANCHO_ETIQUETA = 63 * mm
        ALTO_ETIQUETA = 29 * mm
        MARGEN_IZQUIERDO = 8 * mm
        MARGEN_SUPERIOR = 12 * mm
        ESPACIO_HORIZONTAL = 5 * mm
        ESPACIO_VERTICAL = 4 * mm
        
        # Crear PDF
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        if quintal_id:
            # ========================================
            # GENERAR ETIQUETAS PARA QUINTAL
            # ========================================
            quintal = Quintal.objects.get(id=quintal_id)
            codigo = quintal.codigo_unico
            nombre_producto = quintal.producto.nombre
            peso_unitario = 1.0
            unidad = quintal.unidad_medida.abreviatura
            precio = float(quintal.producto.precio_por_unidad_peso or 0)
            fecha = quintal.fecha_recepcion.strftime('%d/%m/%Y')
            filename = f'etiquetas_{quintal.codigo_unico}.pdf'
            
            etiqueta_num = 0
            
            while etiqueta_num < cantidad:
                for fila in range(ETIQUETAS_POR_COLUMNA):
                    for columna in range(ETIQUETAS_POR_FILA):
                        if etiqueta_num >= cantidad:
                            break
                        
                        # Calcular posición
                        x = MARGEN_IZQUIERDO + columna * (ANCHO_ETIQUETA + ESPACIO_HORIZONTAL)
                        y = letter[1] - MARGEN_SUPERIOR - (fila + 1) * (ALTO_ETIQUETA + ESPACIO_VERTICAL)
                        
                        # === NOMBRE DEL PRODUCTO (ARRIBA) ===
                        pdf.setFont("Helvetica-Bold", 8)
                        nombre_truncado = nombre_producto[:22] + '...' if len(nombre_producto) > 22 else nombre_producto
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 24*mm, nombre_truncado)
                        
                        # === CÓDIGO DE BARRAS (CENTRO) ===
                        barcode_width = 45 * mm
                        barcode_height = 10 * mm
                        barcode_x = x + (ANCHO_ETIQUETA - barcode_width) / 2
                        barcode_y = y + 12 * mm
                        
                        try:
                            barcode_obj = code128.Code128(codigo, barWidth=0.32*mm, barHeight=barcode_height)
                            barcode_obj.drawOn(pdf, barcode_x, barcode_y)
                        except:
                            pass
                        
                        # === CÓDIGO (DEBAJO DEL BARCODE) ===
                        pdf.setFont("Helvetica-Bold", 6)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 9*mm, codigo)
                        
                        # === PESO ===
                        pdf.setFont("Helvetica", 7)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 6*mm, f"{peso_unitario} {unidad}")
                        
                        # === PRECIO (DESTACADO) ===
                        pdf.setFont("Helvetica-Bold", 10)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 3*mm, f"${precio:.2f}")
                        
                        # === FECHA (ABAJO) ===
                        pdf.setFont("Helvetica", 5)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 0.5*mm, f"{fecha}")
                        
                        etiqueta_num += 1
                
                if etiqueta_num < cantidad:
                    pdf.showPage()
            
        elif producto_id:
            # ========================================
            # GENERAR ETIQUETAS PARA PRODUCTO NORMAL
            # ========================================
            producto = Producto.objects.get(id=producto_id)
            codigo = producto.codigo_barras
            nombre_producto = producto.nombre
            precio = float(producto.precio_unitario or 0)
            fecha = datetime.now().strftime('%d/%m/%Y')
            filename = f'etiquetas_{producto.codigo_barras}.pdf'
            
            etiqueta_num = 0
            
            while etiqueta_num < cantidad:
                for fila in range(ETIQUETAS_POR_COLUMNA):
                    for columna in range(ETIQUETAS_POR_FILA):
                        if etiqueta_num >= cantidad:
                            break
                        
                        # Calcular posición
                        x = MARGEN_IZQUIERDO + columna * (ANCHO_ETIQUETA + ESPACIO_HORIZONTAL)
                        y = letter[1] - MARGEN_SUPERIOR - (fila + 1) * (ALTO_ETIQUETA + ESPACIO_VERTICAL)
                        
                        # === NOMBRE DEL PRODUCTO (ARRIBA) ===
                        pdf.setFont("Helvetica-Bold", 8)
                        nombre_truncado = nombre_producto[:22] + '...' if len(nombre_producto) > 22 else nombre_producto
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 24*mm, nombre_truncado)
                        
                        # === CÓDIGO DE BARRAS (CENTRO) ===
                        barcode_width = 45 * mm
                        barcode_height = 10 * mm
                        barcode_x = x + (ANCHO_ETIQUETA - barcode_width) / 2
                        barcode_y = y + 12 * mm
                        
                        try:
                            barcode_obj = code128.Code128(codigo, barWidth=0.32*mm, barHeight=barcode_height)
                            barcode_obj.drawOn(pdf, barcode_x, barcode_y)
                        except:
                            pass
                        
                        # === CÓDIGO (DEBAJO DEL BARCODE) ===
                        pdf.setFont("Helvetica-Bold", 6)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 9*mm, codigo)
                        
                        # === PRECIO (DESTACADO) ===
                        pdf.setFont("Helvetica-Bold", 11)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 4*mm, f"${precio:.2f}")
                        
                        # === FECHA (ABAJO) ===
                        pdf.setFont("Helvetica", 5)
                        pdf.drawCentredString(x + ANCHO_ETIQUETA / 2, y + 1*mm, f"{fecha}")
                        
                        etiqueta_num += 1
                
                if etiqueta_num < cantidad:
                    pdf.showPage()
            
        else:
            return JsonResponse({'error': 'Parámetros inválidos'}, status=400)
        
        # Finalizar PDF
        pdf.save()
        buffer.seek(0)
        
        # Retornar PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Quintal.DoesNotExist:
        return JsonResponse({'error': 'Quintal no encontrado'}, status=404)
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        import traceback
        print("=" * 80)
        print("ERROR GENERANDO PDF:")
        print(traceback.format_exc())
        print("=" * 80)
        return JsonResponse({
            'error': f'Error generando PDF: {str(e)}',
            'detalle': traceback.format_exc()
        }, status=500)
@ensure_csrf_cookie
def api_quintales_disponibles(request):
    """
    API para obtener quintales disponibles de un producto
    
    Parámetros GET:
        - producto_id (UUID): ID del producto del cual obtener quintales
    
    Retorna:
        JSON con lista de quintales disponibles y sus detalles
    
    Uso:
        GET /panel/api/inventario/quintales-disponibles/?producto_id=<uuid>
    """
    from apps.inventory_management.models import Quintal
    from django.http import JsonResponse
    
    # Obtener producto_id del request
    producto_id = request.GET.get('producto_id')
    
    # Validar que se envió el producto_id
    if not producto_id:
        return JsonResponse({
            'success': False,
            'error': 'Se requiere producto_id'
        }, status=400)
    
    try:
        # Obtener quintales disponibles del producto
        quintales = Quintal.objects.filter(
            producto_id=producto_id,
            estado='DISPONIBLE'
        ).select_related(
            'producto',
            'proveedor',
            'unidad_medida'
        ).order_by('fecha_recepcion')  # FIFO: primero los más antiguos
        
        # Construir lista de quintales para respuesta
        quintales_data = []
        for quintal in quintales:
            quintales_data.append({
                'id': str(quintal.id),
                'codigo_unico': quintal.codigo_unico,
                'peso_inicial': float(quintal.peso_inicial),
                'peso_actual': float(quintal.peso_actual),
                'unidad_medida': quintal.unidad_medida.abreviatura if quintal.unidad_medida else 'lb',
                'costo_por_unidad': float(quintal.costo_por_unidad),
                'fecha_recepcion': quintal.fecha_recepcion.strftime('%d/%m/%Y'),
                'proveedor': quintal.proveedor.nombre_comercial if quintal.proveedor else 'Sin proveedor',
                'lote': quintal.lote_proveedor or 'Sin lote',
            })
        
        # Retornar respuesta exitosa
        return JsonResponse({
            'success': True,
            'quintales': quintales_data,
            'total': len(quintales_data)
        })
        
    except Exception as e:
        # Manejar errores
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
@ensure_csrf_cookie
def api_procesar_entrada_unificada(request):
    """API para procesar entrada unificada de inventario - VERSIÓN CORREGIDA PARA QUINTALES"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    import json
    from django.db import transaction
    from django.db.models import Q  # ✅ IMPORT NECESARIO PARA FILTROS
    from apps.inventory_management.models import (
        Producto, Categoria, Marca, Proveedor, ProductoNormal, MovimientoInventario,
        Quintal, UnidadMedida  # ✅ AGREGAR QUINTAL Y UNIDADMEDIDA
    )
    from apps.authentication.models import Usuario
    from decimal import Decimal
    from django.utils import timezone
    
    try:
        # Leer datos del FormData
        productos_json = request.POST.get('productos')
        
        if not productos_json:
            return JsonResponse({
                'success': False,
                'error': 'No se recibieron datos de productos'
            })
        
        productos_data = json.loads(productos_json)
        
        print("=" * 80)
        print(f"📦 PRODUCTOS RECIBIDOS: {len(productos_data)}")
        print("=" * 80)
        
        if not productos_data:
            return JsonResponse({
                'success': False,
                'error': 'No hay productos para procesar'
            })
        
        # Obtener usuario del sistema
        usuario = Usuario.objects.filter(rol__codigo__in=['ADMIN', 'SUPERVISOR']).first()
        if not usuario:
            usuario = Usuario.objects.first()
        
        if not usuario:
            return JsonResponse({
                'success': False,
                'error': 'No hay usuarios en el sistema'
            })
        
        productos_creados = 0
        productos_reabastecidos = 0
        quintales_creados = 0  # ✅ NUEVO CONTADOR
        quintales_reabastecidos = 0  # ✅ NUEVO CONTADOR
        codigos_generados = []
        errores = []
        
        with transaction.atomic():
            for idx, prod_data in enumerate(productos_data):
                print(f"\n{'='*60}")
                print(f"🔄 PROCESANDO PRODUCTO {idx + 1}/{len(productos_data)}")
                print(f"📝 Datos: {prod_data}")
                
                try:
                    # Validar datos requeridos
                    if not prod_data.get('nombre'):
                        error_msg = f"Producto {idx + 1}: Falta el nombre"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    # Obtener marca
                    marca_id = prod_data.get('marca_id')
                    if not marca_id:
                        error_msg = f"Producto {idx + 1}: Falta la marca"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    try:
                        marca = Marca.objects.get(id=marca_id)
                        print(f"✅ Marca encontrada: {marca.nombre}")
                    except Marca.DoesNotExist:
                        error_msg = f"Producto {idx + 1}: Marca no encontrada"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    # Obtener categoría
                    if not prod_data.get('categoria_id'):
                        error_msg = f"Producto {idx + 1}: Falta la categoría"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    try:
                        categoria = Categoria.objects.get(id=prod_data['categoria_id'])
                        print(f"✅ Categoría encontrada: {categoria.nombre}")
                    except Categoria.DoesNotExist:
                        error_msg = f"Producto {idx + 1}: Categoría no encontrada"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    # Obtener proveedor
                    if not prod_data.get('proveedor_id'):
                        error_msg = f"Producto {idx + 1}: Falta el proveedor"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    try:
                        proveedor = Proveedor.objects.get(id=prod_data['proveedor_id'])
                        print(f"✅ Proveedor encontrado: {proveedor.nombre_comercial}")
                    except Proveedor.DoesNotExist:
                        error_msg = f"Producto {idx + 1}: Proveedor no encontrado"
                        print(f"❌ {error_msg}")
                        errores.append(error_msg)
                        continue
                    
                    tipo_inventario = prod_data.get('tipo_inventario', 'NORMAL')
                    
                    # ========================================
                    # 🌾 PROCESAR QUINTAL
                    # ========================================
                    if tipo_inventario == 'QUINTAL':
                        print(f"🌾 PROCESANDO QUINTAL")
                        
                        # Obtener unidad de medida
                        unidad_codigo = prod_data.get('unidad_medida')
                        if not unidad_codigo:
                            error_msg = f"Producto {idx + 1}: Falta la unidad de medida"
                            print(f"❌ {error_msg}")
                            errores.append(error_msg)
                            continue
                        
                        try:
                            # Buscar por abreviatura o nombre
                            unidad_medida = UnidadMedida.objects.filter(
                                Q(abreviatura=unidad_codigo) | Q(nombre__icontains=unidad_codigo)
                            ).first()
                            
                            if not unidad_medida:
                                error_msg = f"Producto {idx + 1}: Unidad de medida no encontrada: {unidad_codigo}"
                                print(f"❌ {error_msg}")
                                errores.append(error_msg)
                                continue
                            
                            print(f"✅ Unidad de medida: {unidad_medida.nombre}")
                        except Exception as e:
                            error_msg = f"Producto {idx + 1}: Error buscando unidad: {str(e)}"
                            print(f"❌ {error_msg}")
                            errores.append(error_msg)
                            continue
                        
                        peso_inicial = Decimal(str(prod_data.get('cantidad', 0)))
                        costo_total = Decimal(str(prod_data.get('costo_unitario', 0))) * peso_inicial
                        precio_por_unidad_peso = Decimal(str(prod_data.get('precio_venta', 0)))
                        
                        # ✅ BUSCAR SI EL PRODUCTO YA EXISTE
                        nombre_producto = prod_data['nombre'].strip()
                        producto_existente = Producto.objects.filter(
                            nombre__iexact=nombre_producto,
                            marca=marca,
                            categoria=categoria,
                            tipo_inventario='QUINTAL',
                            activo=True
                        ).first()
                        
                        # ✅ OBTENER IMAGEN SI EXISTE
                        imagen_file = None
                        if prod_data.get('tiene_imagen'):
                            imagen_key = f'imagen_{idx}'
                            if imagen_key in request.FILES:
                                imagen_file = request.FILES[imagen_key]
                                print(f"📷 Imagen recibida: {imagen_file.name}")
                        
                        if not producto_existente:
                            # ✅ CREAR PRODUCTO NUEVO
                            from apps.inventory_management.utils.barcode_generator import BarcodeGenerator
                            codigo_barras = BarcodeGenerator.generar_codigo_producto()
                            
                            producto_data = {
                                'codigo_barras': codigo_barras,
                                'nombre': nombre_producto,
                                'descripcion': prod_data.get('descripcion', ''),
                                'marca': marca,
                                'categoria': categoria,
                                'proveedor': proveedor,
                                'tipo_inventario': 'QUINTAL',
                                'unidad_medida_base': unidad_medida,
                                'precio_por_unidad_peso': precio_por_unidad_peso,
                                'iva': Decimal(str(prod_data.get('iva', '0.00'))),
                                'activo': True,
                                'usuario_registro': usuario
                            }
                            
                            if imagen_file:
                                producto_data['imagen'] = imagen_file
                            
                            producto = Producto.objects.create(**producto_data)
                            print(f"✅ Producto QUINTAL creado: {producto.nombre}")
                            productos_creados += 1
                        else:
                            producto = producto_existente
                            print(f"✅ Producto QUINTAL existente: {producto.nombre}")
                            
                            # Actualizar precio si cambió
                            if producto.precio_por_unidad_peso != precio_por_unidad_peso:
                                producto.precio_por_unidad_peso = precio_por_unidad_peso
                                producto.save()
                            
                            productos_reabastecidos += 1
                        
                        # ✅ CREAR QUINTAL
                        from apps.inventory_management.utils.barcode_generator import BarcodeGenerator
                        codigo_quintal = BarcodeGenerator.generar_codigo_quintal(producto)
                        
                        quintal = Quintal.objects.create(
                            codigo_unico=codigo_quintal,
                            producto=producto,
                            proveedor=proveedor,
                            peso_inicial=peso_inicial,
                            peso_actual=peso_inicial,
                            unidad_medida=unidad_medida,
                            costo_total=costo_total,
                            costo_por_unidad=costo_total / peso_inicial if peso_inicial > 0 else Decimal('0'),
                            fecha_recepcion=timezone.now(),
                            fecha_vencimiento=prod_data.get('fecha_vencimiento') or None,
                            lote_proveedor=prod_data.get('lote', ''),
                            numero_factura_compra='',
                            usuario_registro=usuario,
                            estado='DISPONIBLE'
                        )
                        
                        print(f"✅ QUINTAL CREADO: {quintal.codigo_unico}")
                        print(f"   Peso: {quintal.peso_inicial} {quintal.unidad_medida.abreviatura}")
                        print(f"   Costo: ${quintal.costo_total}")
                        quintales_creados += 1
                        
                        # ✅ GENERAR CÓDIGOS DE BARRAS
                        cantidad_etiquetas = int(peso_inicial)  # 1 etiqueta por unidad
                        
                        codigos_generados.append({
                            'tipo': 'QUINTAL',
                            'codigo_base': quintal.codigo_unico,
                            'producto_nombre': producto.nombre,
                            'cantidad_codigos': cantidad_etiquetas,
                            'cantidad_stock': float(peso_inicial),
                            'unidad_medida': unidad_medida.abreviatura,
                            'pdf_url': f'/panel/api/inventario/generar-pdf-codigos/?quintal_id={quintal.id}&cantidad={cantidad_etiquetas}',
                            'tipo_operacion': 'NUEVO_QUINTAL'
                        })
                    
                    # ========================================
                    # 📦 PROCESAR PRODUCTO NORMAL
                    # ========================================
                    else:
                        print(f"📦 PROCESANDO PRODUCTO NORMAL")
                        
                        nombre_producto = prod_data['nombre'].strip()
                        producto_existente = Producto.objects.filter(
                            nombre__iexact=nombre_producto,
                            marca=marca,
                            categoria=categoria,
                            tipo_inventario='NORMAL',
                            activo=True
                        ).first()
                        
                        cantidad = int(prod_data.get('cantidad', 0))
                        costo_unitario = Decimal(str(prod_data.get('costo_unitario', '0')))
                        precio_venta = Decimal(str(prod_data.get('precio_venta', '0')))
                        
                        # Obtener imagen
                        imagen_file = None
                        if prod_data.get('tiene_imagen'):
                            imagen_key = f'imagen_{idx}'
                            if imagen_key in request.FILES:
                                imagen_file = request.FILES[imagen_key]
                        
                        if producto_existente:
                            # REABASTECER
                            producto = producto_existente
                            
                            if producto.precio_unitario != precio_venta:
                                producto.precio_unitario = precio_venta
                            
                            if imagen_file:
                                if producto.imagen:
                                    producto.imagen.delete(save=False)
                                producto.imagen = imagen_file
                            
                            producto.save()
                            
                            # Reabastecer inventario
                            try:
                                producto_normal = producto.inventario_normal
                                stock_antes = producto_normal.stock_actual
                                
                                producto_normal.stock_actual += cantidad
                                
                                # Costo promedio ponderado
                                if stock_antes > 0:
                                    costo_total_anterior = stock_antes * producto_normal.costo_unitario
                                    costo_total_nuevo = cantidad * costo_unitario
                                    stock_total = stock_antes + cantidad
                                    producto_normal.costo_unitario = (costo_total_anterior + costo_total_nuevo) / stock_total
                                else:
                                    producto_normal.costo_unitario = costo_unitario
                                
                                producto_normal.fecha_ultima_entrada = timezone.now()
                                
                                if prod_data.get('lote'):
                                    producto_normal.lote = prod_data.get('lote')
                                if prod_data.get('fecha_vencimiento'):
                                    producto_normal.fecha_vencimiento = prod_data.get('fecha_vencimiento')
                                
                                producto_normal.save()
                                
                                # Registrar movimiento
                                MovimientoInventario.objects.create(
                                    producto_normal=producto_normal,
                                    tipo_movimiento='ENTRADA_COMPRA',
                                    cantidad=cantidad,
                                    stock_antes=stock_antes,
                                    stock_despues=producto_normal.stock_actual,
                                    costo_unitario=costo_unitario,
                                    costo_total=cantidad * costo_unitario,
                                    usuario=usuario,
                                    observaciones=f"Reabastecimiento - {prod_data.get('lote', 'Sin lote')}"
                                )
                                
                                productos_reabastecidos += 1
                                
                            except ProductoNormal.DoesNotExist:
                                producto_normal = ProductoNormal.objects.create(
                                    producto=producto,
                                    stock_actual=cantidad,
                                    stock_minimo=10,
                                    costo_unitario=costo_unitario,
                                    lote=prod_data.get('lote', ''),
                                    fecha_vencimiento=prod_data.get('fecha_vencimiento') or None,
                                    fecha_ultima_entrada=timezone.now()
                                )
                                
                                MovimientoInventario.objects.create(
                                    producto_normal=producto_normal,
                                    tipo_movimiento='ENTRADA_COMPRA',
                                    cantidad=cantidad,
                                    stock_antes=0,
                                    stock_despues=cantidad,
                                    costo_unitario=costo_unitario,
                                    costo_total=cantidad * costo_unitario,
                                    usuario=usuario,
                                    observaciones=f"Primer inventario - {prod_data.get('lote', 'Sin lote')}"
                                )
                                
                                productos_reabastecidos += 1
                        
                        else:
                            # CREAR NUEVO
                            from apps.inventory_management.utils.barcode_generator import BarcodeGenerator
                            codigo_barras = BarcodeGenerator.generar_codigo_producto()
                            
                            producto_data = {
                                'codigo_barras': codigo_barras,
                                'nombre': nombre_producto,
                                'descripcion': prod_data.get('descripcion', ''),
                                'marca': marca,
                                'categoria': categoria,
                                'proveedor': proveedor,
                                'tipo_inventario': 'NORMAL',
                                'precio_unitario': precio_venta,
                                'iva': Decimal(str(prod_data.get('iva', '0.00'))),
                                'activo': True,
                                'usuario_registro': usuario
                            }
                            
                            if imagen_file:
                                producto_data['imagen'] = imagen_file
                            
                            producto = Producto.objects.create(**producto_data)
                            
                            producto_normal = ProductoNormal.objects.create(
                                producto=producto,
                                stock_actual=cantidad,
                                stock_minimo=10,
                                costo_unitario=costo_unitario,
                                lote=prod_data.get('lote', ''),
                                fecha_vencimiento=prod_data.get('fecha_vencimiento') or None,
                                fecha_ultima_entrada=timezone.now()
                            )
                            
                            MovimientoInventario.objects.create(
                                producto_normal=producto_normal,
                                tipo_movimiento='ENTRADA_COMPRA',
                                cantidad=cantidad,
                                stock_antes=0,
                                stock_despues=cantidad,
                                costo_unitario=costo_unitario,
                                costo_total=cantidad * costo_unitario,
                                usuario=usuario,
                                observaciones=f"Entrada inicial - {prod_data.get('lote', 'Sin lote')}"
                            )
                            
                            productos_creados += 1
                        
                        # Generar códigos
                        cantidad_codigos = int(prod_data.get('cantidad_codigos', cantidad))
                        
                        codigos_generados.append({
                            'tipo': 'NORMAL',
                            'codigo_base': producto.codigo_barras,
                            'producto_nombre': producto.nombre,
                            'cantidad_codigos': cantidad_codigos,
                            'cantidad_stock': cantidad,
                            'unidad_medida': 'UNIDAD',
                            'pdf_url': f'/panel/api/inventario/generar-pdf-codigos/?producto_id={producto.id}&cantidad={cantidad_codigos}',
                            'tipo_operacion': 'REABASTECIMIENTO' if producto_existente else 'NUEVO'
                        })
                    
                except Exception as e:
                    error_msg = f"Producto {idx + 1} ({prod_data.get('nombre', 'Sin nombre')}): {str(e)}"
                    print(f"❌ ERROR: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    errores.append(error_msg)
                    continue
        
        print("\n" + "=" * 80)
        print(f"✅ RESUMEN FINAL:")
        print(f"   - Productos NUEVOS: {productos_creados}")
        print(f"   - Productos REABASTECIDOS: {productos_reabastecidos}")
        print(f"   - Quintales CREADOS: {quintales_creados}")
        print(f"   - Códigos generados: {len(codigos_generados)}")
        print(f"   - Errores: {len(errores)}")
        print("=" * 80)
        
        return JsonResponse({
            'success': True,
            'productos_creados': productos_creados,
            'productos_reabastecidos': productos_reabastecidos,
            'quintales_creados': quintales_creados,
            'codigos_generados': codigos_generados,
            'errores': errores,
            'mensaje': f'{productos_creados} nuevos, {productos_reabastecidos} reabastecidos, {quintales_creados} quintales'
        })
        
    except json.JSONDecodeError as e:
        print(f"❌ ERROR JSON: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error al decodificar JSON: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        error_detalle = traceback.format_exc()
        print("=" * 80)
        print("❌ ERROR CRÍTICO:")
        print(error_detalle)
        print("=" * 80)
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar inventario: {str(e)}'
        }, status=500)

# ============================================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================================

@ensure_csrf_cookie
@auth_required
def movimientos_inventario_view(request):
    """Vista principal de movimientos de inventario con filtros"""
    from apps.inventory_management.models import MovimientoInventario, Producto
    from apps.authentication.models import Usuario
    from django.db.models import Q, Sum, Count
    from django.core.paginator import Paginator
    from decimal import Decimal
    
    # Base queryset
    movimientos = MovimientoInventario.objects.select_related(
        'producto_normal__producto',
        'usuario'
    ).all().order_by('-fecha_movimiento')
    
    # ========================================
    # FILTROS
    # ========================================
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    tipo_movimiento = request.GET.get('tipo_movimiento', '')
    producto_id = request.GET.get('producto', '')
    usuario_id = request.GET.get('usuario', '')
    search = request.GET.get('search', '')
    
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_inicio)
    
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_fin)
    
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    
    if producto_id:
        movimientos = movimientos.filter(producto_normal__producto_id=producto_id)
    
    if usuario_id:
        movimientos = movimientos.filter(usuario_id=usuario_id)
    
    if search:
        movimientos = movimientos.filter(
            Q(producto_normal__producto__nombre__icontains=search) |
            Q(observaciones__icontains=search)
        )
    
    # ========================================
    # ESTADÍSTICAS
    # ========================================
    total_movimientos = movimientos.count()
    
    entradas = movimientos.filter(
        tipo_movimiento__in=['ENTRADA_COMPRA', 'ENTRADA_AJUSTE', 'ENTRADA_DEVOLUCION']
    ).aggregate(
        total=Sum('cantidad'),
        count=Count('id')
    )
    
    salidas = movimientos.filter(
        tipo_movimiento__in=['SALIDA_VENTA', 'SALIDA_AJUSTE', 'SALIDA_MERMA', 'SALIDA_DEVOLUCION']
    ).aggregate(
        total=Sum('cantidad'),
        count=Count('id')
    )
    
    total_entradas = abs(entradas['total'] or 0)
    count_entradas = entradas['count'] or 0
    
    total_salidas = abs(salidas['total'] or 0)
    count_salidas = salidas['count'] or 0
    
    # Movimientos del día
    hoy = timezone.now().date()
    movimientos_hoy = MovimientoInventario.objects.filter(
        fecha_movimiento__date=hoy
    ).count()
    
    # ========================================
    # PAGINACIÓN
    # ========================================
    paginator = Paginator(movimientos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # ========================================
    # DATOS PARA FORMULARIOS
    # ========================================
    productos = Producto.objects.filter(
        tipo_inventario='NORMAL',
        activo=True
    ).order_by('nombre')
    
    usuarios = Usuario.objects.filter(is_active=True).order_by('nombres')
    
    # Tipos de movimiento
    tipos_movimiento = [
        ('', 'Todos'),
        ('ENTRADA_COMPRA', 'Entrada por Compra'),
        ('ENTRADA_DEVOLUCION', 'Entrada por Devolución'),
        ('ENTRADA_AJUSTE', 'Entrada por Ajuste'),
        ('SALIDA_VENTA', 'Salida por Venta'),
        ('SALIDA_DEVOLUCION', 'Salida por Devolución'),
        ('SALIDA_MERMA', 'Salida por Merma'),
        ('SALIDA_AJUSTE', 'Salida por Ajuste'),
    ]
    
    context = {
        'page_obj': page_obj,
        'movimientos': page_obj,
        'total_movimientos': total_movimientos,
        'total_entradas': total_entradas,
        'count_entradas': count_entradas,
        'total_salidas': total_salidas,
        'count_salidas': count_salidas,
        'movimientos_hoy': movimientos_hoy,
        'productos': productos,
        'usuarios': usuarios,
        'tipos_movimiento': tipos_movimiento,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'tipo_movimiento_selected': tipo_movimiento,
        'producto_selected': producto_id,
        'usuario_selected': usuario_id,
        'search': search,
    }
    
    return render(request, 'custom_admin/inventario/movimientos_list.html', context)


@ensure_csrf_cookie
@auth_required
def movimiento_detalle_api(request, pk):
    """API para obtener detalles de un movimiento de inventario"""
    from apps.inventory_management.models import MovimientoInventario
    from django.http import JsonResponse
    
    try:
        movimiento = MovimientoInventario.objects.select_related(
            'producto_normal__producto',
            'usuario'
        ).get(pk=pk)
        
        data = {
            'success': True,
            'movimiento': {
                'fecha_movimiento': movimiento.fecha_movimiento.strftime('%d/%m/%Y %H:%M'),
                'tipo_movimiento': movimiento.get_tipo_movimiento_display(),
                'tipo_movimiento_code': movimiento.tipo_movimiento,
                'producto_nombre': movimiento.producto_normal.producto.nombre,
                'producto_codigo': movimiento.producto_normal.producto.codigo_barras or 'Sin código',
                'cantidad': str(movimiento.cantidad),
                'stock_antes': str(movimiento.stock_antes),
                'stock_despues': str(movimiento.stock_despues),
                'costo_unitario': str(movimiento.costo_unitario),
                'costo_total': str(movimiento.costo_total),
                'usuario': movimiento.usuario.get_full_name() if movimiento.usuario else 'Sistema',
                'referencia': movimiento.venta.numero_venta if movimiento.venta else 'N/A',
                'observaciones': movimiento.observaciones or 'Sin observaciones',
            }
        }
        return JsonResponse(data)
        
    except MovimientoInventario.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Movimiento no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@ensure_csrf_cookie
@auth_required
def exportar_movimiento_excel(request, pk):
    """Exporta un movimiento individual a Excel"""
    from apps.inventory_management.models import MovimientoInventario
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse
    
    try:
        movimiento = MovimientoInventario.objects.select_related(
            'producto_normal__producto',
            'usuario'
        ).get(pk=pk)
        
        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Movimiento"
        
        # Encabezado
        ws['A1'] = 'DETALLE DE MOVIMIENTO DE INVENTARIO'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')
        
        # Información
        row = 3
        ws[f'A{row}'] = 'Fecha:'
        ws[f'B{row}'] = movimiento.fecha_movimiento.strftime('%d/%m/%Y %H:%M')
        row += 1
        
        ws[f'A{row}'] = 'Tipo:'
        ws[f'B{row}'] = movimiento.get_tipo_movimiento_display()
        row += 1
        
        ws[f'A{row}'] = 'Producto:'
        ws[f'B{row}'] = movimiento.producto_normal.producto.nombre
        row += 1
        
        ws[f'A{row}'] = 'Cantidad:'
        ws[f'B{row}'] = movimiento.cantidad
        row += 1
        
        ws[f'A{row}'] = 'Stock Antes:'
        ws[f'B{row}'] = movimiento.stock_antes
        row += 1
        
        ws[f'A{row}'] = 'Stock Después:'
        ws[f'B{row}'] = movimiento.stock_despues
        row += 1
        
        ws[f'A{row}'] = 'Usuario:'
        ws[f'B{row}'] = movimiento.usuario.get_full_name() if movimiento.usuario else 'Sistema'
        
        # Ajustar columnas
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 40
        
        # Respuesta
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="movimiento_{pk}.xlsx"'
        wb.save(response)
        return response
        
    except MovimientoInventario.DoesNotExist:
        messages.error(request, 'Movimiento no encontrado')
        return redirect('custom_admin:movimientos_inventario')


@ensure_csrf_cookie
@auth_required
def exportar_movimiento_pdf(request, pk):
    """Exporta un movimiento individual a PDF"""
    from apps.inventory_management.models import MovimientoInventario
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from django.http import HttpResponse
    
    try:
        movimiento = MovimientoInventario.objects.select_related(
            'producto_normal__producto',
            'usuario'
        ).get(pk=pk)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="movimiento_{pk}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph('<b>DETALLE DE MOVIMIENTO DE INVENTARIO</b>', styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Datos
        data = [
            ['Fecha:', movimiento.fecha_movimiento.strftime('%d/%m/%Y %H:%M')],
            ['Tipo:', movimiento.get_tipo_movimiento_display()],
            ['Producto:', movimiento.producto_normal.producto.nombre],
            ['Cantidad:', str(movimiento.cantidad)],
            ['Stock Antes:', str(movimiento.stock_antes)],
            ['Stock Después:', str(movimiento.stock_despues)],
            ['Costo Unitario:', f'${movimiento.costo_unitario}'],
            ['Costo Total:', f'${movimiento.costo_total}'],
            ['Usuario:', movimiento.usuario.get_full_name() if movimiento.usuario else 'Sistema'],
        ]
        
        table = Table(data, colWidths=[150, 350])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response
        
    except MovimientoInventario.DoesNotExist:
        messages.error(request, 'Movimiento no encontrado')
        return redirect('custom_admin:movimientos_inventario')


@ensure_csrf_cookie
@auth_required
def exportar_movimientos_excel_general(request):
    """Exportar todos los movimientos filtrados a Excel"""
    from apps.inventory_management.models import MovimientoInventario
    from django.http import HttpResponse
    from django.db.models import Q
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from datetime import datetime
    from io import BytesIO
    
    # Obtener filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    producto_id = request.GET.get('producto')
    usuario_id = request.GET.get('usuario')
    search = request.GET.get('search')
    
    # Filtrar movimientos
    movimientos = MovimientoInventario.objects.select_related(
        'producto_normal__producto',
        'usuario'
    ).all().order_by('-fecha_movimiento')
    
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_fin)
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    if producto_id:
        movimientos = movimientos.filter(producto_normal__producto_id=producto_id)
    if usuario_id:
        movimientos = movimientos.filter(usuario_id=usuario_id)
    if search:
        movimientos = movimientos.filter(
            Q(producto_normal__producto__nombre__icontains=search) |
            Q(observaciones__icontains=search)
        )
    
    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    
    # Estilos
    header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, size=14)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # TÍTULO
    ws.merge_cells('A1:J1')
    ws['A1'] = f"REPORTE DE MOVIMIENTOS DE INVENTARIO - {datetime.now().strftime('%d/%m/%Y')}"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    
    # HEADERS
    headers = ['Fecha', 'Tipo', 'Producto', 'Cantidad', 'Stock Antes', 
               'Stock Después', 'Costo Unit.', 'Costo Total', 'Usuario', 'Observaciones']
    
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # DATOS
    row = 4
    for mov in movimientos:
        ws.cell(row=row, column=1, value=mov.fecha_movimiento.strftime('%d/%m/%Y %H:%M')).border = border
        ws.cell(row=row, column=2, value=mov.get_tipo_movimiento_display()).border = border
        ws.cell(row=row, column=3, value=mov.producto_normal.producto.nombre).border = border
        ws.cell(row=row, column=4, value=float(mov.cantidad)).border = border
        ws.cell(row=row, column=4).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=5, value=float(mov.stock_antes)).border = border
        ws.cell(row=row, column=5).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=6, value=float(mov.stock_despues)).border = border
        ws.cell(row=row, column=6).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=7, value=float(mov.costo_unitario)).border = border
        ws.cell(row=row, column=7).number_format = '$#,##0.00'
        ws.cell(row=row, column=8, value=float(mov.costo_total)).border = border
        ws.cell(row=row, column=8).number_format = '$#,##0.00'
        ws.cell(row=row, column=9, value=mov.usuario.get_full_name() if mov.usuario else 'Sistema').border = border
        ws.cell(row=row, column=10, value=mov.observaciones or 'N/A').border = border
        row += 1
    
    # Ajustar anchos
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 20
    ws.column_dimensions['J'].width = 25
    
    # Preparar respuesta
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"movimientos_inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


@ensure_csrf_cookie
@auth_required
def exportar_movimientos_pdf_general(request):
    """Exportar todos los movimientos filtrados a PDF"""
    from apps.inventory_management.models import MovimientoInventario
    from django.http import HttpResponse
    from django.db.models import Q
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    from datetime import datetime
    
    # Obtener filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    producto_id = request.GET.get('producto')
    usuario_id = request.GET.get('usuario')
    search = request.GET.get('search')
    
    # Filtrar movimientos
    movimientos = MovimientoInventario.objects.select_related(
        'producto_normal__producto',
        'usuario'
    ).all().order_by('-fecha_movimiento')
    
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_fin)
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    if producto_id:
        movimientos = movimientos.filter(producto_normal__producto_id=producto_id)
    if usuario_id:
        movimientos = movimientos.filter(usuario_id=usuario_id)
    if search:
        movimientos = movimientos.filter(
            Q(producto_normal__producto__nombre__icontains=search) |
            Q(observaciones__icontains=search)
        )
    
    # Limitar a 200 registros para PDF
    movimientos = movimientos[:200]
    
    # Crear buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    title = Paragraph(f"REPORTE DE MOVIMIENTOS DE INVENTARIO - {datetime.now().strftime('%d/%m/%Y')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10))
    
    # Tabla de movimientos
    data = [['Fecha', 'Tipo', 'Producto', 'Cant.', 'Stock Antes', 'Stock Después', 'Usuario']]
    
    for mov in movimientos:
        data.append([
            mov.fecha_movimiento.strftime('%d/%m/%Y'),
            mov.get_tipo_movimiento_display()[:15],
            mov.producto_normal.producto.nombre[:25],
            str(mov.cantidad),
            str(mov.stock_antes),
            str(mov.stock_despues),
            (mov.usuario.get_full_name() if mov.usuario else 'Sistema')[:20],
        ])
    
    table = Table(data, colWidths=[1*inch, 1.3*inch, 2*inch, 0.7*inch, 1*inch, 1*inch, 1.5*inch])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Body
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (3, 1), (5, -1), 'CENTER'),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    # Preparar respuesta
    buffer.seek(0)
    filename = f"movimientos_inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


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
# APIs MOCK PARA DASHBOARD
# ========================================

@ensure_csrf_cookie
def api_dashboard_stats(request):
    """Estadísticas del dashboard"""
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

@ensure_csrf_cookie
def api_alertas_count(request):
    """API para obtener el conteo de alertas activas"""
    try:
        from apps.stock_alert_system.models import Alerta
        
        # Contar alertas no leídas
        count = Alerta.objects.filter(
            resuelta=False,
            activa=True
        ).count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'count': 0
        })

# API para quintales (agregar al final del archivo)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.inventory_management.models import Quintal
from apps.sales_management.quintal_service import QuintalSalesService
from decimal import Decimal
import json

@csrf_exempt
def api_quintales_por_producto(request, producto_id):
    """Obtiene quintales disponibles de un producto"""
    try:
        quintales = Quintal.objects.filter(
            producto_id=producto_id,
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).order_by('fecha_recepcion')  # FIFO
        
        data = []
        for q in quintales:
            data.append({
                'id': str(q.id),
                'codigo': q.codigo_unico,
                'peso_actual': float(q.peso_actual),
                'unidad': q.unidad_medida.abreviatura,
                'precio_por_unidad': float(q.producto.precio_por_unidad_peso)
            })
        
        return JsonResponse({'success': True, 'quintales': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
def api_calcular_quintal(request):
    """Calcula conversión entre peso y dinero"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        data = json.loads(request.body)
        quintal_id = data.get('quintal_id')
        tipo = data.get('tipo')  # 'peso_a_dinero' o 'dinero_a_peso'
        valor = Decimal(str(data.get('valor', 0)))
        
        quintal = Quintal.objects.get(id=quintal_id)
        service = QuintalSalesService()
        
        if tipo == 'peso_a_dinero':
            dinero = service.calcular_dinero_por_peso(quintal, valor)
            return JsonResponse({
                'success': True,
                'peso': float(valor),
                'dinero': float(dinero),
                'unidad': quintal.unidad_medida.abreviatura
            })
        else:  # dinero_a_peso
            peso = service.calcular_peso_por_dinero(quintal, valor)
            # Validar disponibilidad
            if peso > quintal.peso_actual:
                return JsonResponse({
                    'success': False,
                    'error': f'Peso insuficiente. Máximo disponible: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}'
                })
            return JsonResponse({
                'success': True,
                'peso': float(peso),
                'dinero': float(valor),
                'unidad': quintal.unidad_medida.abreviatura
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
