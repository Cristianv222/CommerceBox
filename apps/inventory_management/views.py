# apps/inventory_management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib import messages
from django.db.models import Q, Sum, F, Count, Avg, Case, When, DecimalField
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta

from .models import (
    Categoria, Proveedor, UnidadMedida, Producto,
    Quintal, MovimientoQuintal, ProductoNormal,
    MovimientoInventario, Compra, DetalleCompra
)
from .forms import (
    CategoriaForm, ProveedorForm, ProductoForm,
    QuintalForm, ProductoNormalForm, BuscarCodigoBarrasForm,
    AjusteInventarioQuintalForm, AjusteInventarioNormalForm,
    CompraForm
)
from .services.barcode_service import BarcodeService
from .utils.barcode_generator import BarcodeGenerator
from .mixins import (
    InventarioAccessMixin, InventarioEditMixin, InventarioDeleteMixin,
    AjaxInventarioMixin, FormMessagesMixin, DeleteMessageMixin
)
from .decorators import inventario_access_required, ajax_inventario_access_required


# ============================================================================
# DASHBOARD DE INVENTARIO
# ============================================================================

class InventoryDashboardView(InventarioAccessMixin, TemplateView):
    """Dashboard principal del inventario"""
    template_name = 'inventory/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas generales
        context['total_productos'] = Producto.objects.filter(activo=True).count()
        context['total_categorias'] = Categoria.objects.filter(activa=True).count()
        context['total_proveedores'] = Proveedor.objects.filter(activo=True).count()
        
        # Quintales
        quintales_disponibles = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__gt=0
        )
        context['total_quintales_disponibles'] = quintales_disponibles.count()
        
        # Valor de inventario de quintales
        valor_quintales = quintales_disponibles.aggregate(
            valor=Sum(F('peso_actual') * F('costo_por_unidad'))
        )['valor'] or Decimal('0')
        context['valor_quintales'] = valor_quintales
        
        # Productos normales
        productos_normales = ProductoNormal.objects.filter(stock_actual__gt=0)
        context['total_productos_normales_stock'] = productos_normales.count()
        
        # Valor de inventario de productos normales
        valor_normales = productos_normales.aggregate(
            valor=Sum(F('stock_actual') * F('costo_unitario'))
        )['valor'] or Decimal('0')
        context['valor_normales'] = valor_normales
        
        # Valor total
        context['valor_total_inventario'] = valor_quintales + valor_normales
        
        # Alertas
        context['quintales_criticos'] = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__lte=F('peso_inicial') * 0.1,
            peso_actual__gt=0
        ).count()
        
        context['productos_criticos'] = ProductoNormal.objects.filter(
            stock_actual__lte=F('stock_minimo'),
            stock_actual__gt=0
        ).count()
        
        # Próximos a vencer (7 días)
        fecha_limite = timezone.now().date() + timedelta(days=7)
        context['proximos_vencer'] = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=timezone.now().date()
        ).count()
        
        # Últimos movimientos
        context['ultimos_movimientos_quintales'] = MovimientoQuintal.objects.select_related(
            'quintal', 'quintal__producto', 'usuario'
        ).order_by('-fecha_movimiento')[:5]
        
        context['ultimos_movimientos_normales'] = MovimientoInventario.objects.select_related(
            'producto_normal', 'producto_normal__producto', 'usuario'
        ).order_by('-fecha_movimiento')[:5]
        
        # Productos más vendidos (últimos 30 días)
        fecha_hace_30_dias = timezone.now() - timedelta(days=30)
        
        # Top quintales más vendidos
        context['top_quintales'] = MovimientoQuintal.objects.filter(
            tipo_movimiento='VENTA',
            fecha_movimiento__gte=fecha_hace_30_dias
        ).values(
            'quintal__producto__nombre'
        ).annotate(
            total_vendido=Sum('peso_movimiento')
        ).order_by('-total_vendido')[:5]
        
        # Top productos normales más vendidos
        context['top_productos_normales'] = MovimientoInventario.objects.filter(
            tipo_movimiento='SALIDA_VENTA',
            fecha_movimiento__gte=fecha_hace_30_dias
        ).values(
            'producto_normal__producto__nombre'
        ).annotate(
            total_vendido=Sum('cantidad')
        ).order_by('-total_vendido')[:5]
        
        return context


# ============================================================================
# VISTAS DE CATEGORÍAS
# ============================================================================

class CategoriaListView(InventarioAccessMixin, ListView):
    """Lista de categorías"""
    model = Categoria
    template_name = 'inventory/categoria_list.html'
    context_object_name = 'categorias'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )
        
        return queryset.order_by('orden', 'nombre')


class CategoriaCreateView(InventarioEditMixin, FormMessagesMixin, CreateView):
    """Crear categoría"""
    model = Categoria
    form_class = CategoriaForm
    template_name = 'inventory/categoria_form.html'
    success_url = reverse_lazy('inventory_management:categoria_list')
    success_message = "Categoría '{object.nombre}' creada exitosamente."


class CategoriaUpdateView(InventarioEditMixin, FormMessagesMixin, UpdateView):
    """Editar categoría"""
    model = Categoria
    form_class = CategoriaForm
    template_name = 'inventory/categoria_form.html'
    success_url = reverse_lazy('inventory_management:categoria_list')
    success_message = "Categoría '{object.nombre}' actualizada exitosamente."


class CategoriaDeleteView(InventarioDeleteMixin, DeleteMessageMixin, DeleteView):
    """Eliminar categoría"""
    model = Categoria
    template_name = 'inventory/categoria_confirm_delete.html'
    success_url = reverse_lazy('inventory_management:categoria_list')
    delete_message = "Categoría '{object.nombre}' eliminada exitosamente."


# ============================================================================
# VISTAS DE PROVEEDORES
# ============================================================================

class ProveedorListView(InventarioAccessMixin, ListView):
    """Lista de proveedores"""
    model = Proveedor
    template_name = 'inventory/proveedor_list.html'
    context_object_name = 'proveedores'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(nombre_comercial__icontains=search) |
                Q(razon_social__icontains=search) |
                Q(ruc_nit__icontains=search)
            )
        
        return queryset.order_by('nombre_comercial')


class ProveedorCreateView(InventarioEditMixin, FormMessagesMixin, CreateView):
    """Crear proveedor"""
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'inventory/proveedor_form.html'
    success_url = reverse_lazy('inventory_management:proveedor_list')
    success_message = "Proveedor '{object.nombre_comercial}' creado exitosamente."


class ProveedorDetailView(InventarioAccessMixin, DetailView):
    """Detalle de proveedor"""
    model = Proveedor
    template_name = 'inventory/proveedor_detail.html'
    context_object_name = 'proveedor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proveedor = self.get_object()
        
        # Quintales del proveedor
        context['quintales'] = Quintal.objects.filter(
            proveedor=proveedor
        ).order_by('-fecha_recepcion')[:10]
        
        # Compras del proveedor
        context['compras'] = Compra.objects.filter(
            proveedor=proveedor
        ).order_by('-fecha_compra')[:10]
        
        # Estadísticas
        context['total_compras'] = Compra.objects.filter(
            proveedor=proveedor,
            estado='RECIBIDA'
        ).count()
        
        context['valor_total_compras'] = Compra.objects.filter(
            proveedor=proveedor,
            estado='RECIBIDA'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        return context


class ProveedorUpdateView(InventarioEditMixin, FormMessagesMixin, UpdateView):
    """Editar proveedor"""
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'inventory/proveedor_form.html'
    success_message = "Proveedor '{object.nombre_comercial}' actualizado exitosamente."
    
    def get_success_url(self):
        return reverse('inventory_management:proveedor_detail', kwargs={'pk': self.object.pk})


class ProveedorDeleteView(InventarioDeleteMixin, DeleteMessageMixin, DeleteView):
    """Eliminar proveedor"""
    model = Proveedor
    template_name = 'inventory/proveedor_confirm_delete.html'
    success_url = reverse_lazy('inventory_management:proveedor_list')
    delete_message = "Proveedor '{object.nombre_comercial}' eliminado exitosamente."


# ============================================================================
# VISTAS DE PRODUCTOS (Maestro)
# ============================================================================

class ProductoListView(InventarioAccessMixin, ListView):
    """Lista de productos"""
    model = Producto
    template_name = 'inventory/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('categoria', 'proveedor')
        
        # Filtros
        search = self.request.GET.get('search')
        categoria_id = self.request.GET.get('categoria')
        tipo = self.request.GET.get('tipo')
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo_barras__icontains=search) |
                Q(descripcion__icontains=search)
            )
        
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        
        if tipo:
            queryset = queryset.filter(tipo_inventario=tipo)
        
        return queryset.order_by('nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(activa=True)
        context['search'] = self.request.GET.get('search', '')
        context['categoria_selected'] = self.request.GET.get('categoria', '')
        context['tipo_selected'] = self.request.GET.get('tipo', '')
        return context


class ProductoCreateView(InventarioEditMixin, FormMessagesMixin, CreateView):
    """Crear producto"""
    model = Producto
    form_class = ProductoForm
    template_name = 'inventory/producto_form.html'
    success_url = reverse_lazy('inventory_management:producto_list')
    success_message = "Producto '{object.nombre}' creado exitosamente."
    
    def form_valid(self, form):
        form.instance.usuario_registro = self.request.user
        return super().form_valid(form)


class ProductoDetailView(InventarioAccessMixin, DetailView):
    """Detalle de producto"""
    model = Producto
    template_name = 'inventory/producto_detail.html'
    context_object_name = 'producto'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto = self.get_object()
        
        if producto.es_quintal():
            # Quintales del producto
            context['quintales'] = Quintal.objects.filter(
                producto=producto
            ).order_by('-fecha_recepcion')
            
            # Peso total disponible
            context['peso_total_disponible'] = Quintal.objects.filter(
                producto=producto,
                estado='DISPONIBLE'
            ).aggregate(total=Sum('peso_actual'))['total'] or Decimal('0')
            
            # Últimos movimientos
            context['ultimos_movimientos'] = MovimientoQuintal.objects.filter(
                quintal__producto=producto
            ).select_related('quintal', 'usuario').order_by('-fecha_movimiento')[:10]
            
        else:
            # Inventario normal
            try:
                context['inventario'] = ProductoNormal.objects.get(producto=producto)
                
                # Últimos movimientos
                context['ultimos_movimientos'] = MovimientoInventario.objects.filter(
                    producto_normal__producto=producto
                ).select_related('usuario').order_by('-fecha_movimiento')[:10]
            except ProductoNormal.DoesNotExist:
                context['inventario'] = None
        
        return context


class ProductoUpdateView(InventarioEditMixin, FormMessagesMixin, UpdateView):
    """Editar producto"""
    model = Producto
    form_class = ProductoForm
    template_name = 'inventory/producto_form.html'
    success_message = "Producto '{object.nombre}' actualizado exitosamente."
    
    def get_success_url(self):
        return reverse('inventory_management:producto_detail', kwargs={'pk': self.object.pk})


class ProductoDeleteView(InventarioDeleteMixin, DeleteMessageMixin, DeleteView):
    """Eliminar producto"""
    model = Producto
    template_name = 'inventory/producto_confirm_delete.html'
    success_url = reverse_lazy('inventory_management:producto_list')
    delete_message = "Producto '{object.nombre}' eliminado exitosamente."


# ============================================================================
# VISTAS DE QUINTALES
# ============================================================================

class QuintalListView(InventarioAccessMixin, ListView):
    """Lista de quintales"""
    model = Quintal
    template_name = 'inventory/quintal_list.html'
    context_object_name = 'quintales'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'producto', 'producto__categoria', 'proveedor', 'unidad_medida'
        )
        
        # Filtros
        search = self.request.GET.get('search')
        estado = self.request.GET.get('estado')
        producto_id = self.request.GET.get('producto')
        proveedor_id = self.request.GET.get('proveedor')
        criticos = self.request.GET.get('criticos')
        
        if search:
            queryset = queryset.filter(
                Q(codigo_unico__icontains=search) |
                Q(producto__nombre__icontains=search) |
                Q(lote_proveedor__icontains=search)
            )
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        
        if criticos == '1':
            queryset = queryset.filter(
                estado='DISPONIBLE',
                peso_actual__lte=F('peso_inicial') * 0.1,
                peso_actual__gt=0
            )
        
        return queryset.order_by('-fecha_recepcion')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['productos_quintal'] = Producto.objects.filter(
            tipo_inventario='QUINTAL',
            activo=True
        )
        context['proveedores'] = Proveedor.objects.filter(activo=True)
        
        # Filtros actuales
        context['search'] = self.request.GET.get('search', '')
        context['estado_selected'] = self.request.GET.get('estado', '')
        context['producto_selected'] = self.request.GET.get('producto', '')
        context['proveedor_selected'] = self.request.GET.get('proveedor', '')
        context['criticos'] = self.request.GET.get('criticos', '')
        
        return context


class QuintalCreateView(InventarioEditMixin, FormMessagesMixin, CreateView):
    """Crear/Registrar entrada de quintal"""
    model = Quintal
    form_class = QuintalForm
    template_name = 'inventory/quintal_form.html'
    success_url = reverse_lazy('inventory_management:quintal_list')
    
    def get_success_message(self):
        return (
            f"Quintal '{self.object.codigo_unico}' registrado exitosamente. "
            f"Peso: {self.object.peso_inicial} {self.object.unidad_medida.abreviatura}"
        )
    
    def form_valid(self, form):
        form.instance.usuario_registro = self.request.user
        form.instance.peso_actual = form.instance.peso_inicial
        form.instance.estado = 'DISPONIBLE'
        return super().form_valid(form)


class QuintalDetailView(InventarioAccessMixin, DetailView):
    """Detalle de quintal con trazabilidad completa"""
    model = Quintal
    template_name = 'inventory/quintal_detail.html'
    context_object_name = 'quintal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quintal = self.get_object()
        
        # Todos los movimientos del quintal
        context['movimientos'] = MovimientoQuintal.objects.filter(
            quintal=quintal
        ).select_related('usuario', 'unidad_medida').order_by('-fecha_movimiento')
        
        # Estadísticas
        context['total_vendido'] = MovimientoQuintal.objects.filter(
            quintal=quintal,
            tipo_movimiento='VENTA'
        ).aggregate(total=Sum('peso_movimiento'))['total'] or Decimal('0')
        
        context['porcentaje_restante'] = quintal.porcentaje_restante()
        context['peso_vendido'] = quintal.peso_vendido()
        
        # Ventas realizadas desde este quintal
        context['ventas'] = MovimientoQuintal.objects.filter(
            quintal=quintal,
            tipo_movimiento='VENTA',
            venta__isnull=False
        ).select_related('venta', 'usuario').order_by('-fecha_movimiento')
        
        return context


class QuintalUpdateView(InventarioEditMixin, FormMessagesMixin, UpdateView):
    """Editar información de quintal (solo campos editables)"""
    model = Quintal
    form_class = QuintalForm
    template_name = 'inventory/quintal_form.html'
    success_message = "Quintal '{object.codigo_unico}' actualizado exitosamente."
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Deshabilitar campos que no se deben editar después de crear
        form.fields['peso_inicial'].disabled = True
        form.fields['producto'].disabled = True
        return form
    
    def get_success_url(self):
        return reverse('inventory_management:quintal_detail', kwargs={'pk': self.object.pk})


class QuintalMovimientosView(InventarioAccessMixin, DetailView):
    """Vista de movimientos de un quintal específico"""
    model = Quintal
    template_name = 'inventory/quintal_movimientos.html'
    context_object_name = 'quintal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quintal = self.get_object()
        
        # Filtrar movimientos por tipo si es necesario
        tipo = self.request.GET.get('tipo')
        movimientos = MovimientoQuintal.objects.filter(quintal=quintal)
        
        if tipo:
            movimientos = movimientos.filter(tipo_movimiento=tipo)
        
        context['movimientos'] = movimientos.select_related(
            'usuario', 'unidad_medida', 'venta'
        ).order_by('-fecha_movimiento')
        
        context['tipo_selected'] = tipo
        
        return context


# ============================================================================
# VISTAS DE PRODUCTOS NORMALES
# ============================================================================

class ProductoNormalListView(InventarioAccessMixin, ListView):
    """Lista de productos normales con stock"""
    model = ProductoNormal
    template_name = 'inventory/producto_normal_list.html'
    context_object_name = 'productos_normales'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('producto', 'producto__categoria')
        
        # Filtros
        search = self.request.GET.get('search')
        categoria_id = self.request.GET.get('categoria')
        estado = self.request.GET.get('estado')
        
        if search:
            queryset = queryset.filter(
                Q(producto__nombre__icontains=search) |
                Q(producto__codigo_barras__icontains=search) |
                Q(lote__icontains=search)
            )
        
        if categoria_id:
            queryset = queryset.filter(producto__categoria_id=categoria_id)
        
        if estado == 'CRITICO':
            queryset = queryset.filter(stock_actual__lte=F('stock_minimo'))
        elif estado == 'BAJO':
            queryset = queryset.filter(
                stock_actual__gt=F('stock_minimo'),
                stock_actual__lte=F('stock_minimo') * 2
            )
        elif estado == 'AGOTADO':
            queryset = queryset.filter(stock_actual=0)
        
        return queryset.order_by('producto__nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(activa=True)
        context['search'] = self.request.GET.get('search', '')
        context['categoria_selected'] = self.request.GET.get('categoria', '')
        context['estado_selected'] = self.request.GET.get('estado', '')
        return context


class ProductoNormalCreateView(InventarioEditMixin, FormMessagesMixin, CreateView):
    """Crear inventario para producto normal"""
    model = ProductoNormal
    form_class = ProductoNormalForm
    template_name = 'inventory/producto_normal_form.html'
    success_url = reverse_lazy('inventory_management:producto_normal_list')
    
    def get_success_message(self):
        return (
            f"Inventario para '{self.object.producto.nombre}' creado exitosamente. "
            f"Stock inicial: {self.object.stock_actual} unidades"
        )


class ProductoNormalDetailView(InventarioAccessMixin, DetailView):
    """Detalle de producto normal con movimientos"""
    model = ProductoNormal
    template_name = 'inventory/producto_normal_detail.html'
    context_object_name = 'producto_normal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto_normal = self.get_object()
        
        # Movimientos
        context['movimientos'] = MovimientoInventario.objects.filter(
            producto_normal=producto_normal
        ).select_related('usuario').order_by('-fecha_movimiento')[:20]
        
        # Estadísticas
        context['total_entradas'] = MovimientoInventario.objects.filter(
            producto_normal=producto_normal,
            cantidad__gt=0
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        context['total_salidas'] = MovimientoInventario.objects.filter(
            producto_normal=producto_normal,
            cantidad__lt=0
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        context['valor_inventario'] = producto_normal.valor_inventario()
        context['estado_stock'] = producto_normal.estado_stock()
        
        return context


class ProductoNormalUpdateView(InventarioEditMixin, FormMessagesMixin, UpdateView):
    """Editar producto normal"""
    model = ProductoNormal
    form_class = ProductoNormalForm
    template_name = 'inventory/producto_normal_form.html'
    success_message = "Producto actualizado exitosamente."
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # No permitir cambiar el producto
        form.fields['producto'].disabled = True
        return form
    
    def get_success_url(self):
        return reverse('inventory_management:producto_normal_detail', kwargs={'pk': self.object.pk})


class ProductoNormalMovimientosView(InventarioAccessMixin, DetailView):
    """Vista de movimientos de producto normal"""
    model = ProductoNormal
    template_name = 'inventory/producto_normal_movimientos.html'
    context_object_name = 'producto_normal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto_normal = self.get_object()
        
        # Filtrar por tipo si es necesario
        tipo = self.request.GET.get('tipo')
        movimientos = MovimientoInventario.objects.filter(producto_normal=producto_normal)
        
        if tipo:
            movimientos = movimientos.filter(tipo_movimiento=tipo)
        
        context['movimientos'] = movimientos.select_related(
            'usuario', 'venta', 'compra'
        ).order_by('-fecha_movimiento')
        
        context['tipo_selected'] = tipo
        
        return context


# ============================================================================
# BÚSQUEDA POR CÓDIGO DE BARRAS
# ============================================================================

class BuscarCodigoBarrasView(InventarioAccessMixin, TemplateView):
    """Vista para buscar productos por código de barras"""
    template_name = 'inventory/buscar_codigo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BuscarCodigoBarrasForm()
        
        codigo = self.request.GET.get('codigo_barras')
        if codigo:
            resultado = BarcodeService.buscar_por_codigo(codigo)
            context['resultado'] = resultado
            context['codigo_buscado'] = codigo
        
        return context


class BuscarCodigoAPIView(AjaxInventarioMixin, View):
    """API para buscar código de barras (AJAX)"""
    
    def get(self, request):
        codigo = request.GET.get('codigo', '').strip()
        
        if not codigo:
            return JsonResponse({
                'success': False,
                'error': 'Código vacío'
            })
        
        resultado = BarcodeService.buscar_por_codigo(codigo)
        
        # Preparar respuesta JSON
        response_data = {
            'success': resultado['encontrado'],
            'tipo': resultado['tipo'],
            'mensaje': resultado['mensaje'],
            'puede_vender': resultado['puede_vender']
        }
        
        # Agregar datos según tipo
        if resultado['encontrado']:
            if resultado['tipo'] == 'QUINTAL_PRODUCTO':
                # Es un producto a granel
                producto = resultado['data']
                response_data['producto'] = {
                    'id': str(producto.id),
                    'nombre': producto.nombre,
                    'precio': float(producto.precio_por_unidad_peso),
                    'unidad': producto.unidad_medida_base.abreviatura,
                    'codigo_barras': producto.codigo_barras
                }
                
                # Quintales disponibles
                quintales = resultado['quintales_disponibles']
                response_data['quintales'] = [
                    {
                        'id': str(q.id),
                        'codigo': q.codigo_unico,
                        'peso_actual': float(q.peso_actual),
                        'unidad': q.unidad_medida.abreviatura
                    }
                    for q in quintales[:5]  # Primeros 5
                ]
            
            elif resultado['tipo'] == 'QUINTAL_INDIVIDUAL':
                # Es un quintal específico
                quintal = resultado['data']
                response_data['quintal'] = {
                    'id': str(quintal.id),
                    'codigo': quintal.codigo_unico,
                    'producto_nombre': quintal.producto.nombre,
                    'peso_actual': float(quintal.peso_actual),
                    'unidad': quintal.unidad_medida.abreviatura,
                    'precio': float(quintal.producto.precio_por_unidad_peso)
                }
            
            elif resultado['tipo'] == 'PRODUCTO_NORMAL':
                # Es un producto normal
                producto = resultado['data']
                inventario = resultado['inventario']
                response_data['producto'] = {
                    'id': str(producto.id),
                    'nombre': producto.nombre,
                    'precio': float(producto.precio_unitario),
                    'stock': inventario.stock_actual if inventario else 0,
                    'codigo_barras': producto.codigo_barras
                }
        
        return JsonResponse(response_data)


# ============================================================================
# AJUSTES DE INVENTARIO
# ============================================================================

class AjusteQuintalView(InventarioEditMixin, TemplateView):
    """Vista para ajustar peso de quintales"""
    template_name = 'inventory/ajuste_quintal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AjusteInventarioQuintalForm()
        return context
    
    @transaction.atomic
    def post(self, request):
        form = AjusteInventarioQuintalForm(request.POST)
        
        if form.is_valid():
            quintal = form.cleaned_data['quintal']
            tipo_ajuste = form.cleaned_data['tipo_ajuste']
            peso_ajuste = form.cleaned_data['peso_ajuste']
            observaciones = form.cleaned_data['observaciones']
            
            # Capturar estado antes
            peso_antes = quintal.peso_actual
            
            # Realizar ajuste
            if tipo_ajuste == 'AJUSTE_POSITIVO':
                quintal.peso_actual += peso_ajuste
                peso_movimiento = peso_ajuste
            else:  # AJUSTE_NEGATIVO o MERMA
                quintal.peso_actual -= peso_ajuste
                peso_movimiento = -peso_ajuste
            
            quintal.save()
            peso_despues = quintal.peso_actual
            
            # Registrar movimiento
            MovimientoQuintal.objects.create(
                quintal=quintal,
                tipo_movimiento=tipo_ajuste,
                peso_movimiento=peso_movimiento,
                peso_antes=peso_antes,
                peso_despues=peso_despues,
                unidad_medida=quintal.unidad_medida,
                usuario=request.user,
                observaciones=observaciones
            )
            
            messages.success(
                request,
                f"Ajuste realizado exitosamente. "
                f"Quintal {quintal.codigo_unico}: {peso_antes} → {peso_despues} {quintal.unidad_medida.abreviatura}"
            )
            return redirect('inventory_management:quintal_detail', pk=quintal.pk)
        
        return render(request, self.template_name, {'form': form})


class AjusteProductoNormalView(InventarioEditMixin, TemplateView):
    """Vista para ajustar stock de productos normales"""
    template_name = 'inventory/ajuste_producto_normal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AjusteInventarioNormalForm()
        return context
    
    @transaction.atomic
    def post(self, request):
        form = AjusteInventarioNormalForm(request.POST)
        
        if form.is_valid():
            producto_normal = form.cleaned_data['producto_normal']
            tipo_ajuste = form.cleaned_data['tipo_ajuste']
            cantidad = form.cleaned_data['cantidad']
            observaciones = form.cleaned_data['observaciones']
            
            # Capturar estado antes
            stock_antes = producto_normal.stock_actual
            
            # Realizar ajuste
            if tipo_ajuste == 'ENTRADA_AJUSTE':
                producto_normal.stock_actual += cantidad
                cantidad_movimiento = cantidad
            else:  # SALIDA_AJUSTE o SALIDA_MERMA
                producto_normal.stock_actual -= cantidad
                cantidad_movimiento = -cantidad
            
            producto_normal.save()
            stock_despues = producto_normal.stock_actual
            
            # Registrar movimiento
            MovimientoInventario.objects.create(
                producto_normal=producto_normal,
                tipo_movimiento=tipo_ajuste,
                cantidad=cantidad_movimiento,
                stock_antes=stock_antes,
                stock_despues=stock_despues,
                costo_unitario=producto_normal.costo_unitario,
                costo_total=abs(cantidad_movimiento) * producto_normal.costo_unitario,
                usuario=request.user,
                observaciones=observaciones
            )
            
            messages.success(
                request,
                f"Ajuste realizado exitosamente. "
                f"{producto_normal.producto.nombre}: {stock_antes} → {stock_despues} unidades"
            )
            return redirect('inventory_management:producto_normal_detail', pk=producto_normal.pk)
        
        return render(request, self.template_name, {'form': form})


# ============================================================================
# VISTAS DE COMPRAS
# ============================================================================

class CompraListView(InventarioAccessMixin, ListView):
    """Lista de compras"""
    model = Compra
    template_name = 'inventory/compra_list.html'
    context_object_name = 'compras'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('proveedor', 'usuario_registro')
        
        # Filtros
        estado = self.request.GET.get('estado')
        proveedor_id = self.request.GET.get('proveedor')
        search = self.request.GET.get('search')
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        
        if search:
            queryset = queryset.filter(
                Q(numero_compra__icontains=search) |
                Q(numero_factura__icontains=search)
            )
        
        return queryset.order_by('-fecha_compra')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proveedores'] = Proveedor.objects.filter(activo=True)
        context['estado_selected'] = self.request.GET.get('estado', '')
        context['proveedor_selected'] = self.request.GET.get('proveedor', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class CompraCreateView(InventarioEditMixin, FormMessagesMixin, CreateView):
    """Crear compra"""
    model = Compra
    form_class = CompraForm
    template_name = 'inventory/compra_form.html'
    success_url = reverse_lazy('inventory_management:compra_list')
    success_message = "Compra '{object.numero_compra}' creada exitosamente."
    
    def form_valid(self, form):
        form.instance.usuario_registro = self.request.user
        form.instance.estado = 'PENDIENTE'
        return super().form_valid(form)


class CompraDetailView(InventarioAccessMixin, DetailView):
    """Detalle de compra"""
    model = Compra
    template_name = 'inventory/compra_detail.html'
    context_object_name = 'compra'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        compra = self.get_object()
        
        # Detalles de la compra
        context['detalles'] = DetalleCompra.objects.filter(
            compra=compra
        ).select_related('producto', 'unidad_medida')
        
        return context


class CompraRecibirView(InventarioEditMixin, DetailView):
    """Vista para recibir una compra y crear quintales/actualizar inventario"""
    model = Compra
    template_name = 'inventory/compra_recibir.html'
    context_object_name = 'compra'
    
    @transaction.atomic
    def post(self, request, pk):
        compra = get_object_or_404(Compra, pk=pk)
        
        if compra.estado != 'PENDIENTE':
            messages.error(request, "Esta compra ya fue procesada.")
            return redirect('inventory_management:compra_detail', pk=pk)
        
        # Procesar cada detalle
        detalles = DetalleCompra.objects.filter(compra=compra)
        
        for detalle in detalles:
            producto = detalle.producto
            
            if producto.es_quintal():
                # Crear quintal
                quintal = Quintal.objects.create(
                    codigo_unico=BarcodeGenerator.generar_codigo_quintal(producto),
                    producto=producto,
                    proveedor=compra.proveedor,
                    peso_inicial=detalle.peso_comprado,
                    peso_actual=detalle.peso_comprado,
                    unidad_medida=detalle.unidad_medida,
                    costo_total=detalle.subtotal,
                    costo_por_unidad=detalle.costo_unitario,
                    fecha_recepcion=timezone.now(),
                    numero_factura_compra=compra.numero_factura,
                    usuario_registro=request.user
                )
                
                detalle.quintal_creado = quintal
                detalle.recibido = True
                detalle.fecha_recepcion = timezone.now()
                detalle.save()
            
            else:
                # Actualizar producto normal
                producto_normal, created = ProductoNormal.objects.get_or_create(
                    producto=producto,
                    defaults={
                        'stock_actual': 0,
                        'stock_minimo': 10,
                        'costo_unitario': detalle.costo_unitario
                    }
                )
                
                stock_antes = producto_normal.stock_actual
                producto_normal.stock_actual += detalle.cantidad_unidades
                producto_normal.fecha_ultima_entrada = timezone.now()
                
                # Actualizar costo promedio ponderado
                if stock_antes > 0:
                    costo_total_anterior = stock_antes * producto_normal.costo_unitario
                    costo_total_nuevo = detalle.cantidad_unidades * detalle.costo_unitario
                    stock_total = stock_antes + detalle.cantidad_unidades
                    producto_normal.costo_unitario = (costo_total_anterior + costo_total_nuevo) / stock_total
                else:
                    producto_normal.costo_unitario = detalle.costo_unitario
                
                producto_normal.save()
                
                # Registrar movimiento
                MovimientoInventario.objects.create(
                    producto_normal=producto_normal,
                    tipo_movimiento='ENTRADA_COMPRA',
                    cantidad=detalle.cantidad_unidades,
                    stock_antes=stock_antes,
                    stock_despues=producto_normal.stock_actual,
                    costo_unitario=detalle.costo_unitario,
                    costo_total=detalle.subtotal,
                    compra=compra,
                    usuario=request.user,
                    observaciones=f"Compra {compra.numero_compra}"
                )
                
                detalle.recibido = True
                detalle.fecha_recepcion = timezone.now()
                detalle.save()
        
        # Actualizar estado de compra
        compra.estado = 'RECIBIDA'
        compra.fecha_recepcion = timezone.now()
        compra.usuario_recepcion = request.user
        compra.save()
        
        messages.success(request, f"Compra {compra.numero_compra} recibida exitosamente.")
        return redirect('inventory_management:compra_detail', pk=pk)


# ============================================================================
# REPORTES
# ============================================================================

class StockCriticoReportView(InventarioAccessMixin, TemplateView):
    """Reporte de productos con stock crítico"""
    template_name = 'inventory/reporte_stock_critico.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Quintales críticos (menos del 10%)
        context['quintales_criticos'] = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__lte=F('peso_inicial') * 0.1,
            peso_actual__gt=0
        ).select_related('producto', 'proveedor', 'unidad_medida')
        
        # Productos normales críticos
        context['productos_criticos'] = ProductoNormal.objects.filter(
            stock_actual__lte=F('stock_minimo'),
            stock_actual__gt=0
        ).select_related('producto', 'producto__categoria')
        
        # Productos agotados
        context['productos_agotados'] = ProductoNormal.objects.filter(
            stock_actual=0
        ).select_related('producto')
        
        return context


class ProximosVencerReportView(InventarioAccessMixin, TemplateView):
    """Reporte de productos próximos a vencer"""
    template_name = 'inventory/reporte_proximos_vencer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Quintales próximos a vencer (próximos 7 días)
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=7)
        
        context['quintales_proximos_vencer'] = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=hoy
        ).select_related('producto', 'proveedor').order_by('fecha_vencimiento')
        
        # Quintales vencidos
        context['quintales_vencidos'] = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__lt=hoy
        ).select_related('producto', 'proveedor')
        
        return context


class ValorInventarioReportView(InventarioAccessMixin, TemplateView):
    """Reporte de valor total del inventario"""
    template_name = 'inventory/reporte_valor_inventario.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Valor de quintales
        quintales = Quintal.objects.filter(estado='DISPONIBLE')
        valor_quintales = quintales.aggregate(
            valor=Sum(F('peso_actual') * F('costo_por_unidad'))
        )['valor'] or Decimal('0')
        
        context['valor_quintales'] = valor_quintales
        context['total_quintales'] = quintales.count()
        
        # Valor de productos normales
        productos_normales = ProductoNormal.objects.all()
        valor_normales = productos_normales.aggregate(
            valor=Sum(F('stock_actual') * F('costo_unitario'))
        )['valor'] or Decimal('0')
        
        context['valor_normales'] = valor_normales
        context['total_productos_normales'] = productos_normales.count()
        
        # Total
        context['valor_total'] = valor_quintales + valor_normales
        
        # Desglose por categoría
        context['valor_por_categoria'] = Categoria.objects.annotate(
            valor_quintales=Sum(
                Case(
                    When(
                        productos__tipo_inventario='QUINTAL',
                        productos__quintales__estado='DISPONIBLE',
                        then=F('productos__quintales__peso_actual') * F('productos__quintales__costo_por_unidad')
                    ),
                    default=0,
                    output_field=DecimalField()
                )
            ),
            valor_normales=Sum(
                Case(
                    When(
                        productos__tipo_inventario='NORMAL',
                        then=F('productos__inventario_normal__stock_actual') * F('productos__inventario_normal__costo_unitario')
                    ),
                    default=0,
                    output_field=DecimalField()
                )
            )
        ).order_by('-valor_quintales')
        
        return context


class TrazabilidadQuintalView(InventarioAccessMixin, DetailView):
    """Vista de trazabilidad completa de un quintal"""
    model = Quintal
    template_name = 'inventory/trazabilidad_quintal.html'
    context_object_name = 'quintal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quintal = self.get_object()
        
        # Todos los movimientos ordenados cronológicamente
        context['movimientos'] = MovimientoQuintal.objects.filter(
            quintal=quintal
        ).select_related('usuario', 'venta').order_by('fecha_movimiento')
        
        # Información de trazabilidad
        context['info_trazabilidad'] = {
            'origen': quintal.origen,
            'proveedor': quintal.proveedor.nombre_comercial,
            'lote': quintal.lote_proveedor,
            'factura': quintal.numero_factura_compra,
            'fecha_recepcion': quintal.fecha_recepcion,
            'fecha_vencimiento': quintal.fecha_vencimiento,
        }
        
        return context


# ============================================================================
# APIs JSON
# ============================================================================

class ProductoBuscarAPIView(AjaxInventarioMixin, View):
    """API para buscar productos (autocomplete)"""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        tipo = request.GET.get('tipo')  # 'QUINTAL' o 'NORMAL'
        
        if len(query) < 2:
            return JsonResponse({'results': []})
        
        productos = Producto.objects.filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query),
            activo=True
        )
        
        if tipo:
            productos = productos.filter(tipo_inventario=tipo)
        
        productos = productos[:10]
        
        results = [
            {
                'id': str(p.id),
                'text': f"{p.nombre} ({p.codigo_barras})",
                'nombre': p.nombre,
                'codigo': p.codigo_barras,
                'tipo': p.tipo_inventario
            }
            for p in productos
        ]
        
        return JsonResponse({'results': results})


class QuintalesDisponiblesAPIView(AjaxInventarioMixin, View):
    """API para obtener quintales disponibles de un producto"""
    
    def get(self, request, producto_id):
        quintales = Quintal.objects.filter(
            producto_id=producto_id,
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).order_by('fecha_recepcion')
        
        data = [
            {
                'id': str(q.id),
                'codigo': q.codigo_unico,
                'peso_actual': float(q.peso_actual),
                'unidad': q.unidad_medida.abreviatura,
                'fecha_recepcion': q.fecha_recepcion.strftime('%Y-%m-%d'),
                'porcentaje': float(q.porcentaje_restante())
            }
            for q in quintales
        ]
        
        return JsonResponse({'quintales': data})


class StockStatusAPIView(AjaxInventarioMixin, View):
    """API para obtener estado de stock de un producto"""
    
    def get(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
            
            if producto.es_quintal():
                peso_total = Quintal.objects.filter(
                    producto=producto,
                    estado='DISPONIBLE'
                ).aggregate(total=Sum('peso_actual'))['total'] or Decimal('0')
                
                return JsonResponse({
                    'tipo': 'QUINTAL',
                    'disponible': float(peso_total) > 0,
                    'cantidad': float(peso_total),
                    'unidad': producto.unidad_medida_base.abreviatura
                })
            else:
                try:
                    inventario = ProductoNormal.objects.get(producto=producto)
                    return JsonResponse({
                        'tipo': 'NORMAL',
                        'disponible': inventario.stock_actual > 0,
                        'cantidad': inventario.stock_actual,
                        'estado': inventario.estado_stock(),
                        'unidad': 'unidades'
                    })
                except ProductoNormal.DoesNotExist:
                    return JsonResponse({
                        'tipo': 'NORMAL',
                        'disponible': False,
                        'cantidad': 0,
                        'estado': 'AGOTADO'
                    })
        
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)