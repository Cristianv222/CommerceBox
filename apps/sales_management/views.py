# apps/sales_management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib import messages
from django.db.models import Q, Sum, Count, F, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta, datetime
import logging
import json

from .models import Cliente, Venta, DetalleVenta, Pago, Devolucion
from .forms import (
    ClienteForm, ClienteSearchForm, VentaForm, BuscarProductoPOSForm,
    AgregarProductoPOSForm, PagoForm, PagoMultipleForm,
    DevolucionForm, AprobarDevolucionForm, VentasFiltroForm, ReporteVentasForm
)
from apps.inventory_management.models import Producto, Quintal, ProductoNormal
from apps.inventory_management.services.barcode_service import BarcodeService

# Importar mixins de inventory_management
from apps.inventory_management.mixins import (
    InventarioAccessMixin, FormMessagesMixin, DeleteMessageMixin
)
from django.contrib.auth.mixins import LoginRequiredMixin
logger = logging.getLogger(__name__)


# ============================================================================
# MIXINS PARA SALES
# ============================================================================

class VentasAccessMixin(InventarioAccessMixin):
    """Mixin para verificar acceso al módulo de ventas"""
    
    def dispatch(self, request, *args, **kwargs):
        # PRIMERO verificar si está autenticado
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        # LUEGO verificar permisos del módulo
        if not request.user.puede_acceder_modulo('sales'):
            messages.error(request, "No tienes permisos para acceder a ventas.")
            return redirect('custom_admin:dashboard')
        
        return super(InventarioAccessMixin, self).dispatch(request, *args, **kwargs)

class VentasAPIAccessMixin:
    """Mixin para verificar acceso a APIs de ventas (devuelve JSON en lugar de redirect)"""
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar autenticación
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'No autenticado. Por favor inicia sesión.',
                'redirect': '/login/'
            }, status=401)
        
        # Verificar permisos del módulo
        if not request.user.puede_acceder_modulo('sales'):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para acceder a ventas.'
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)
# ============================================================================
# DASHBOARD DE VENTAS
# ============================================================================

class SalesDashboardView(VentasAccessMixin, TemplateView):
    """Dashboard principal de ventas"""
    template_name = 'sales/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ventas del día
        hoy = timezone.now().date()
        ventas_hoy = Venta.objects.filter(
            fecha_venta__date=hoy,
            estado='COMPLETADA'
        )
        
        context['ventas_hoy_count'] = ventas_hoy.count()
        context['ventas_hoy_total'] = ventas_hoy.aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        # Ventas del mes
        inicio_mes = timezone.now().replace(day=1)
        ventas_mes = Venta.objects.filter(
            fecha_venta__gte=inicio_mes,
            estado='COMPLETADA'
        )
        
        context['ventas_mes_count'] = ventas_mes.count()
        context['ventas_mes_total'] = ventas_mes.aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        # Ventas pendientes de pago
        context['ventas_pendientes'] = Venta.objects.filter(
            estado='COMPLETADA',
            monto_pagado__lt=F('total')
        ).count()
        
        # Top productos vendidos (últimos 7 días)
        fecha_hace_7_dias = timezone.now() - timedelta(days=7)
        context['top_productos'] = DetalleVenta.objects.filter(
            venta__fecha_venta__gte=fecha_hace_7_dias,
            venta__estado='COMPLETADA'
        ).values(
            'producto__nombre'
        ).annotate(
            total_vendido=Sum('total'),
            cantidad=Count('id')
        ).order_by('-total_vendido')[:5]
        
        # Últimas ventas
        context['ultimas_ventas'] = Venta.objects.select_related(
            'cliente', 'vendedor'
        ).order_by('-fecha_venta')[:10]
        
        # Clientes más frecuentes
        context['top_clientes'] = Cliente.objects.filter(
            activo=True
        ).order_by('-total_compras')[:5]
        
        return context


# ============================================================================
# VISTAS DE CLIENTES
# ============================================================================

class ClienteListView(VentasAccessMixin, ListView):
    """Lista de clientes"""
    model = Cliente
    template_name = 'sales/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(numero_documento__icontains=search) |
                Q(nombres__icontains=search) |
                Q(apellidos__icontains=search) |
                Q(nombre_comercial__icontains=search) |
                Q(telefono__icontains=search)
            )
        
        # Filtro por tipo
        tipo_cliente = self.request.GET.get('tipo_cliente')
        if tipo_cliente:
            queryset = queryset.filter(tipo_cliente=tipo_cliente)
        
        return queryset.order_by('apellidos', 'nombres')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ClienteSearchForm(self.request.GET)
        context['search'] = self.request.GET.get('search', '')
        context['tipo_cliente_selected'] = self.request.GET.get('tipo_cliente', '')
        return context


class ClienteCreateView(VentasAccessMixin, FormMessagesMixin, CreateView):
    """Crear cliente"""
    model = Cliente
    form_class = ClienteForm
    template_name = 'sales/cliente_form.html'
    success_url = reverse_lazy('sales_management:cliente_list')
    success_message = "Cliente '{object}' creado exitosamente."


class ClienteDetailView(VentasAccessMixin, DetailView):
    """Detalle de cliente"""
    model = Cliente
    template_name = 'sales/cliente_detail.html'
    context_object_name = 'cliente'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_object()
        
        # Ventas del cliente
        context['ventas'] = Venta.objects.filter(
            cliente=cliente
        ).order_by('-fecha_venta')[:20]
        
        # Estadísticas
        context['total_ventas'] = Venta.objects.filter(
            cliente=cliente,
            estado='COMPLETADA'
        ).count()
        
        context['saldo_pendiente'] = Venta.objects.filter(
            cliente=cliente,
            estado='COMPLETADA',
            monto_pagado__lt=F('total')
        ).aggregate(
            saldo=Sum(F('total') - F('monto_pagado'))
        )['saldo'] or Decimal('0')
        
        return context


class ClienteUpdateView(VentasAccessMixin, FormMessagesMixin, UpdateView):
    """Editar cliente"""
    model = Cliente
    form_class = ClienteForm
    template_name = 'sales/cliente_form.html'
    success_message = "Cliente '{object}' actualizado exitosamente."
    
    def get_success_url(self):
        return reverse('sales_management:cliente_detail', kwargs={'pk': self.object.pk})


class ClienteDeleteView(VentasAccessMixin, DeleteMessageMixin, DeleteView):
    """Eliminar cliente"""
    model = Cliente
    template_name = 'sales/cliente_confirm_delete.html'
    success_url = reverse_lazy('sales_management:cliente_list')
    delete_message = "Cliente '{object}' eliminado exitosamente."


# ============================================================================
# PUNTO DE VENTA (POS)
# ============================================================================

class POSView(VentasAccessMixin, TemplateView):
    """Vista principal del POS"""
    template_name = 'sales/pos.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Inicializar carrito en sesión si no existe
        if 'carrito' not in self.request.session:
            self.request.session['carrito'] = []
        
        context['carrito'] = self.request.session.get('carrito', [])
        context['total_carrito'] = sum(
            Decimal(str(item['total'])) for item in context['carrito']
        )
        
        # Formularios
        context['form_buscar'] = BuscarProductoPOSForm()
        context['clientes'] = Cliente.objects.filter(activo=True)[:100]
        
        return context


class BuscarProductoPOSView(VentasAccessMixin, View):
    """Buscar producto por código de barras en POS"""
    
    def get(self, request):
        codigo = request.GET.get('codigo', '').strip()
        
        if not codigo:
            return JsonResponse({
                'success': False,
                'error': 'Código vacío'
            })
        
        # Usar servicio de búsqueda de códigos de barras
        resultado = BarcodeService.buscar_por_codigo(codigo)
        
        if not resultado['encontrado']:
            return JsonResponse({
                'success': False,
                'error': resultado['mensaje']
            })
        
        # Preparar respuesta según tipo
        response_data = {
            'success': True,
            'tipo': resultado['tipo']
        }
        
        if resultado['tipo'] == 'QUINTAL_PRODUCTO':
            producto = resultado['data']
            response_data['producto'] = {
                'id': str(producto.id),
                'nombre': producto.nombre,
                'tipo': 'QUINTAL',
                'precio': float(producto.precio_por_unidad_peso),
                'unidad': producto.unidad_medida_base.abreviatura,
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
                for q in quintales[:5]
            ]
        
        elif resultado['tipo'] == 'QUINTAL_INDIVIDUAL':
            quintal = resultado['data']
            response_data['quintal'] = {
                'id': str(quintal.id),
                'codigo': quintal.codigo_unico,
                'producto_id': str(quintal.producto.id),
                'producto_nombre': quintal.producto.nombre,
                'peso_actual': float(quintal.peso_actual),
                'unidad': quintal.unidad_medida.abreviatura,
                'precio': float(quintal.producto.precio_por_unidad_peso)
            }
        
        elif resultado['tipo'] == 'PRODUCTO_NORMAL':
            producto = resultado['data']
            inventario = resultado['inventario']
            response_data['producto'] = {
                'id': str(producto.id),
                'nombre': producto.nombre,
                'tipo': 'NORMAL',
                'precio': float(producto.precio_unitario),
                'stock': inventario.stock_actual if inventario else 0
            }
        
        return JsonResponse(response_data)


class AgregarProductoCarritoView(VentasAccessMixin, View):
    """Agregar producto al carrito de compras"""
    
    def post(self, request):
        try:
            producto_id = request.POST.get('producto_id')
            producto = get_object_or_404(Producto, pk=producto_id)
            
            # Inicializar carrito
            if 'carrito' not in request.session:
                request.session['carrito'] = []
            
            carrito = request.session['carrito']
            
            item = {
                'id': str(producto.id),
                'nombre': producto.nombre,
                'tipo': producto.tipo_inventario,
            }
            
            if producto.es_quintal():
                quintal_id = request.POST.get('quintal_id')
                peso_vendido = Decimal(request.POST.get('peso_vendido', '0'))
                precio = Decimal(request.POST.get('precio', str(producto.precio_por_unidad_peso)))
                
                quintal = get_object_or_404(Quintal, pk=quintal_id)
                
                # Validar stock disponible
                if quintal.peso_actual < peso_vendido:
                    return JsonResponse({
                        'success': False,
                        'error': f'Stock insuficiente. Disponible: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}, Solicitado: {peso_vendido} {quintal.unidad_medida.abreviatura}'
                    })
                
                if quintal.estado != 'DISPONIBLE':
                    return JsonResponse({
                        'success': False,
                        'error': 'El quintal no está disponible para venta'
                    })
                
                item.update({
                    'quintal_id': str(quintal_id),
                    'quintal_codigo': quintal.codigo_unico,
                    'peso_vendido': float(peso_vendido),
                    'unidad': quintal.unidad_medida.abreviatura,
                    'precio_unitario': float(precio),
                    'subtotal': float(peso_vendido * precio),
                })
            
            else:
                cantidad = int(request.POST.get('cantidad_unidades', '1'))
                precio = Decimal(request.POST.get('precio', str(producto.precio_unitario)))
                
                # Validar stock disponible
                try:
                    inventario = producto.inventario_normal
                    if not inventario:
                        return JsonResponse({
                            'success': False,
                            'error': 'Producto sin inventario configurado'
                        })
                    
                    stock_disponible = inventario.stock_actual
                    if stock_disponible < cantidad:
                        return JsonResponse({
                            'success': False,
                            'error': f'Stock insuficiente para {producto.nombre}. Disponible: {stock_disponible} unidades, Solicitado: {cantidad} unidades'
                        })
                    
                except ProductoNormal.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Producto sin inventario configurado'
                    })
                
                item.update({
                    'cantidad': cantidad,
                    'precio_unitario': float(precio),
                    'subtotal': float(cantidad * precio),
                })
            
            # Descuento
            descuento_porcentaje = Decimal(request.POST.get('descuento_porcentaje', '0'))
            descuento_monto = item['subtotal'] * (descuento_porcentaje / 100)
            item['descuento_porcentaje'] = float(descuento_porcentaje)
            item['descuento_monto'] = float(descuento_monto)
            item['total'] = item['subtotal'] - float(descuento_monto)
            
            # Agregar al carrito
            carrito.append(item)
            request.session['carrito'] = carrito
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'carrito_count': len(carrito),
                'total_carrito': float(sum(Decimal(str(i['total'])) for i in carrito))
            })
        
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al agregar producto: {str(e)}'
            })


class EliminarItemCarritoView(VentasAccessMixin, View):
    """Eliminar item del carrito"""
    
    def post(self, request, index):
        carrito = request.session.get('carrito', [])
        
        if 0 <= index < len(carrito):
            carrito.pop(index)
            request.session['carrito'] = carrito
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'carrito_count': len(carrito)
            })
        
        return JsonResponse({
            'success': False,
            'error': 'Item no encontrado'
        })


class VaciarCarritoView(VentasAccessMixin, View):
    """Vaciar el carrito completo"""
    
    def post(self, request):
        request.session['carrito'] = []
        request.session.modified = True
        
        return JsonResponse({'success': True})


class ProcesarVentaPOSView(VentasAccessMixin, View):
    """Procesar venta desde el POS"""
    
    @transaction.atomic
    def post(self, request):
        try:
            carrito = request.session.get('carrito', [])
            
            if not carrito:
                return JsonResponse({
                    'success': False,
                    'error': 'El carrito está vacío'
                })
            
            # Datos de la venta
            cliente_id = request.POST.get('cliente_id')
            tipo_venta = request.POST.get('tipo_venta', 'CONTADO')
            
            cliente = None
            if cliente_id:
                cliente = get_object_or_404(Cliente, pk=cliente_id)
            
            # Importar servicio POS
            from .pos.pos_service import POSService
            
            # Crear venta
            venta = POSService.crear_venta(
                vendedor=request.user,
                cliente=cliente,
                tipo_venta=tipo_venta
            )
            
            # Agregar items del carrito
            for item in carrito:
                producto = Producto.objects.get(pk=item['id'])
                
                try:
                    if item['tipo'] == 'QUINTAL':
                        quintal = Quintal.objects.get(pk=item['quintal_id'])
                        POSService.agregar_item_quintal(
                            venta=venta,
                            producto=producto,
                            quintal=quintal,
                            peso_vendido=Decimal(str(item['peso_vendido'])),
                            precio_por_unidad=Decimal(str(item['precio_unitario'])),
                            descuento_porcentaje=Decimal(str(item.get('descuento_porcentaje', 0)))
                        )
                    else:
                        POSService.agregar_item_normal(
                            venta=venta,
                            producto=producto,
                            cantidad_unidades=item['cantidad'],
                            precio_unitario=Decimal(str(item['precio_unitario'])),
                            descuento_porcentaje=Decimal(str(item.get('descuento_porcentaje', 0)))
                        )
                except (ValueError, ValidationError) as e:
                    # Si hay error de stock, revertir la transacción
                    raise ValueError(f'Error al procesar {producto.nombre}: {str(e)}')
            
            # Procesar pagos
            formas_pago = []
            if request.POST.get('efectivo'):
                formas_pago.append(('EFECTIVO', Decimal(request.POST.get('efectivo'))))
            if request.POST.get('tarjeta_debito'):
                formas_pago.append(('TARJETA_DEBITO', Decimal(request.POST.get('tarjeta_debito'))))
            if request.POST.get('tarjeta_credito'):
                formas_pago.append(('TARJETA_CREDITO', Decimal(request.POST.get('tarjeta_credito'))))
            
            for forma_pago, monto in formas_pago:
                if monto > 0:
                    POSService.procesar_pago(
                        venta=venta,
                        forma_pago=forma_pago,
                        monto=monto,
                        usuario=request.user
                    )
            
            # Finalizar venta (🖨️ IMPRIME AUTOMÁTICAMENTE)
            POSService.finalizar_venta(venta)
            
            # Limpiar carrito
            request.session['carrito'] = []
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'venta_id': str(venta.id),
                'numero_venta': venta.numero_venta,
                'redirect_url': reverse('sales_management:venta_detail', args=[venta.pk])
            })
        
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar venta: {str(e)}'
            })


# ============================================================================
# VISTAS DE VENTAS
# ============================================================================

class VentaListView(VentasAccessMixin, ListView):
    """Lista de ventas"""
    model = Venta
    template_name = 'sales/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'vendedor')
        
        # Filtros
        form = VentasFiltroForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('fecha_inicio'):
                queryset = queryset.filter(fecha_venta__date__gte=form.cleaned_data['fecha_inicio'])
            if form.cleaned_data.get('fecha_fin'):
                queryset = queryset.filter(fecha_venta__date__lte=form.cleaned_data['fecha_fin'])
            if form.cleaned_data.get('estado'):
                queryset = queryset.filter(estado=form.cleaned_data['estado'])
            if form.cleaned_data.get('tipo_venta'):
                queryset = queryset.filter(tipo_venta=form.cleaned_data['tipo_venta'])
            if form.cleaned_data.get('vendedor'):
                queryset = queryset.filter(vendedor=form.cleaned_data['vendedor'])
            if form.cleaned_data.get('cliente'):
                queryset = queryset.filter(cliente=form.cleaned_data['cliente'])
        
        return queryset.order_by('-fecha_venta')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = VentasFiltroForm(self.request.GET)
        
        # Totales
        ventas = self.get_queryset()
        context['total_ventas'] = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')
        context['count_ventas'] = ventas.count()
        
        return context


class VentaDetailView(VentasAccessMixin, DetailView):
    """Detalle de venta"""
    model = Venta
    template_name = 'sales/venta_detail.html'
    context_object_name = 'venta'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.get_object()
        
        # Detalles de la venta
        context['detalles'] = venta.detalles.select_related(
            'producto', 'quintal', 'unidad_medida'
        ).order_by('orden')
        
        # Pagos
        context['pagos'] = venta.pagos.all().order_by('-fecha_pago')
        
        # Devoluciones
        context['devoluciones'] = venta.devoluciones.all().order_by('-fecha_devolucion')
        
        return context


class AnularVentaView(VentasAccessMixin, View):
    """Anular una venta"""
    
    @transaction.atomic
    def post(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        
        # Validaciones
        if venta.estado == 'ANULADA':
            messages.error(request, 'La venta ya está anulada.')
            return redirect('sales_management:venta_detail', pk=pk)
        
        if venta.monto_pagado > 0:
            messages.error(request, 'No se puede anular una venta con pagos registrados.')
            return redirect('sales_management:venta_detail', pk=pk)
        
        # Importar servicio
        from .pos.pos_service import POSService
        
        try:
            POSService.anular_venta(venta, usuario=request.user)
            messages.success(request, f'Venta {venta.numero_venta} anulada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al anular venta: {str(e)}')
        
        return redirect('sales_management:venta_detail', pk=pk)


# ============================================================================
# VISTAS DE DEVOLUCIONES
# ============================================================================

class DevolucionListView(VentasAccessMixin, ListView):
    """Lista de devoluciones"""
    model = Devolucion
    template_name = 'sales/devolucion_list.html'
    context_object_name = 'devoluciones'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'venta_original', 'detalle_venta', 'usuario_solicita'
        )
        
        # Filtros
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset.order_by('-fecha_devolucion')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estado_selected'] = self.request.GET.get('estado', '')
        return context


class DevolucionCreateView(VentasAccessMixin, FormMessagesMixin, CreateView):
    """Crear devolución"""
    model = Devolucion
    form_class = DevolucionForm
    template_name = 'sales/devolucion_form.html'
    success_url = reverse_lazy('sales_management:devolucion_list')
    success_message = "Devolución registrada exitosamente. Pendiente de aprobación."
    
    def form_valid(self, form):
        devolucion = form.save(commit=False)
        
        # Generar número de devolución
        from .pos.pos_service import POSService
        devolucion.numero_devolucion = POSService.generar_numero_devolucion()
        
        # Calcular monto
        detalle = devolucion.detalle_venta
        if detalle.producto.es_quintal():
            precio_unitario = detalle.precio_por_unidad_peso
            devolucion.monto_devolucion = devolucion.cantidad_devuelta * precio_unitario
        else:
            devolucion.monto_devolucion = devolucion.cantidad_devuelta * detalle.precio_unitario
        
        devolucion.usuario_solicita = self.request.user
        
        return super().form_valid(form)


class DevolucionDetailView(VentasAccessMixin, DetailView):
    """Detalle de devolución"""
    model = Devolucion
    template_name = 'sales/devolucion_detail.html'
    context_object_name = 'devolucion'


class AprobarDevolucionView(VentasAccessMixin, View):
    """Aprobar o rechazar devolución"""
    
    @transaction.atomic
    def post(self, request, pk):
        devolucion = get_object_or_404(Devolucion, pk=pk)
        
        if devolucion.estado != 'PENDIENTE':
            messages.error(request, 'La devolución ya fue procesada.')
            return redirect('sales_management:devolucion_detail', pk=pk)
        
        form = AprobarDevolucionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            observaciones = form.cleaned_data.get('observaciones', '')
            
            devolucion.estado = decision
            devolucion.usuario_aprueba = request.user
            devolucion.fecha_procesado = timezone.now()
            devolucion.descripcion += f"\n\nObservaciones: {observaciones}"
            devolucion.save()
            
            # Si se aprueba, procesar la devolución
            if decision == 'APROBADA':
                from .pos.pos_service import POSService
                try:
                    POSService.procesar_devolucion(devolucion, request.user)
                    messages.success(request, 'Devolución aprobada y procesada exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al procesar devolución: {str(e)}')
                    return redirect('sales_management:devolucion_detail', pk=pk)
            else:
                messages.info(request, 'Devolución rechazada.')
            
            return redirect('sales_management:devolucion_detail', pk=pk)
        
        messages.error(request, 'Formulario inválido.')
        return redirect('sales_management:devolucion_detail', pk=pk)


# ============================================================================
# REPORTES
# ============================================================================

class ReporteVentasView(VentasAccessMixin, TemplateView):
    """Reporte de ventas con filtros"""
    template_name = 'sales/reporte_ventas.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = ReporteVentasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            tipo_reporte = form.cleaned_data.get('tipo_reporte')
            agrupar_por = form.cleaned_data.get('agrupar_por')
            
            # Calcular fechas según tipo de reporte
            hoy = timezone.now().date()
            
            if tipo_reporte == 'diario':
                fecha_inicio = hoy
                fecha_fin = hoy
            elif tipo_reporte == 'semanal':
                fecha_inicio = hoy - timedelta(days=7)
                fecha_fin = hoy
            elif tipo_reporte == 'mensual':
                fecha_inicio = hoy.replace(day=1)
                fecha_fin = hoy
            else:  # personalizado
                fecha_inicio = form.cleaned_data.get('fecha_inicio')
                fecha_fin = form.cleaned_data.get('fecha_fin')
            
            # Filtrar ventas
            ventas = Venta.objects.filter(
                fecha_venta__date__gte=fecha_inicio,
                fecha_venta__date__lte=fecha_fin,
                estado='COMPLETADA'
            )
            
            # Estadísticas generales
            context['total_ventas'] = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')
            context['cantidad_ventas'] = ventas.count()
            context['promedio_venta'] = ventas.aggregate(avg=Avg('total'))['avg'] or Decimal('0')
            
            # Agrupar datos
            if agrupar_por == 'vendedor':
                context['datos_agrupados'] = ventas.values(
                    'vendedor__username'
                ).annotate(
                    total=Sum('total'),
                    cantidad=Count('id')
                ).order_by('-total')
                context['label_grupo'] = 'Vendedor'
            
            elif agrupar_por == 'categoria':
                context['datos_agrupados'] = DetalleVenta.objects.filter(
                    venta__in=ventas
                ).values(
                    'producto__categoria__nombre'
                ).annotate(
                    total=Sum('total'),
                    cantidad=Count('id')
                ).order_by('-total')
                context['label_grupo'] = 'Categoría'
            
            elif agrupar_por == 'producto':
                context['datos_agrupados'] = DetalleVenta.objects.filter(
                    venta__in=ventas
                ).values(
                    'producto__nombre'
                ).annotate(
                    total=Sum('total'),
                    cantidad=Count('id')
                ).order_by('-total')[:20]
                context['label_grupo'] = 'Producto'
            
            elif agrupar_por == 'cliente':
                context['datos_agrupados'] = ventas.filter(
                    cliente__isnull=False
                ).values(
                    'cliente__nombres',
                    'cliente__apellidos'
                ).annotate(
                    total=Sum('total'),
                    cantidad=Count('id')
                ).order_by('-total')[:20]
                context['label_grupo'] = 'Cliente'
            
            context['fecha_inicio'] = fecha_inicio
            context['fecha_fin'] = fecha_fin
        
        return context


class ReporteDiarioView(VentasAccessMixin, TemplateView):
    """Reporte de cierre de día"""
    template_name = 'sales/reporte_diario.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Fecha del reporte
        fecha_str = self.request.GET.get('fecha')
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = timezone.now().date()
        
        context['fecha'] = fecha
        
        # Ventas del día
        ventas = Venta.objects.filter(
            fecha_venta__date=fecha,
            estado='COMPLETADA'
        )
        
        # Resumen general
        context['total_ventas'] = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')
        context['cantidad_ventas'] = ventas.count()
        context['promedio_venta'] = ventas.aggregate(avg=Avg('total'))['avg'] or Decimal('0')
        
        # Ventas por vendedor
        context['ventas_por_vendedor'] = ventas.values(
            'vendedor__username'
        ).annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('-total')
        
        # Ventas por forma de pago
        context['ventas_por_forma_pago'] = Pago.objects.filter(
            venta__in=ventas
        ).values('forma_pago').annotate(
            total=Sum('monto')
        ).order_by('-total')
        
        # Top productos vendidos
        context['top_productos'] = DetalleVenta.objects.filter(
            venta__in=ventas
        ).values(
            'producto__nombre'
        ).annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('-total')[:10]
        
        # Ventas por hora
        context['ventas_por_hora'] = ventas.extra(
            select={'hora': "EXTRACT(hour FROM fecha_venta)"}
        ).values('hora').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('hora')
        
        return context


# ============================================================================
# API ENDPOINTS (AJAX)
# ============================================================================

class ClienteAutocompleteView(VentasAccessMixin, View):
    """Autocompletado de clientes"""
    
    def get(self, request):
        term = request.GET.get('term', '')
        
        clientes = Cliente.objects.filter(
            Q(nombres__icontains=term) |
            Q(apellidos__icontains=term) |
            Q(numero_documento__icontains=term) |
            Q(nombre_comercial__icontains=term),
            activo=True
        )[:10]
        
        results = [
            {
                'id': str(c.id),
                'text': str(c),
                'numero_documento': c.numero_documento,
                'tipo_cliente': c.tipo_cliente,
                'descuento_general': float(c.descuento_general)
            }
            for c in clientes
        ]
        
        return JsonResponse({'results': results})


class VentaEstadisticasAPIView(VentasAccessMixin, View):
    """Estadísticas de ventas para gráficos"""
    
    def get(self, request):
        periodo = request.GET.get('periodo', 'mes')  # dia, semana, mes, año
        
        hoy = timezone.now().date()
        
        if periodo == 'dia':
            fecha_inicio = hoy
        elif periodo == 'semana':
            fecha_inicio = hoy - timedelta(days=7)
        elif periodo == 'mes':
            fecha_inicio = hoy.replace(day=1)
        else:  # año
            fecha_inicio = hoy.replace(month=1, day=1)
        
        ventas = Venta.objects.filter(
            fecha_venta__date__gte=fecha_inicio,
            fecha_venta__date__lte=hoy,
            estado='COMPLETADA'
        )
        
        # Ventas por día
        ventas_por_dia = ventas.extra(
            select={'fecha': 'DATE(fecha_venta)'}
        ).values('fecha').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('fecha')
        
        data = {
            'labels': [str(v['fecha']) for v in ventas_por_dia],
            'totales': [float(v['total']) for v in ventas_por_dia],
            'cantidades': [v['cantidad'] for v in ventas_por_dia],
        }
        
        return JsonResponse(data)


class ImprimirTicketView(VentasAccessMixin, View):
    """Imprimir ticket de venta"""
    
    def get(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        
        # Importar servicio de impresión
        from .invoicing.ticket_generator import TicketGenerator
        
        try:
            ticket_html = TicketGenerator.generar_ticket_html(venta)
            return HttpResponse(ticket_html, content_type='text/html')
        except Exception as e:
            messages.error(request, f'Error al generar ticket: {str(e)}')
            return redirect('sales_management:venta_detail', pk=pk)


class ImprimirFacturaView(VentasAccessMixin, View):
    """Imprimir factura de venta"""
    
    def get(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        
        # Importar servicio de facturación
        from .invoicing.invoice_service import InvoiceService
        
        try:
            factura_html = InvoiceService.generar_factura_html(venta)
            return HttpResponse(factura_html, content_type='text/html')
        except Exception as e:
            messages.error(request, f'Error al generar factura: {str(e)}')
            return redirect('sales_management:venta_detail', pk=pk)


# ============================================================================
# 🆕 NUEVAS API ENDPOINTS - IMPRESIÓN Y PROCESAMIENTO
# ============================================================================

class VerificarEstadoImpresionView(VentasAccessMixin, View):
    """
    Verifica el estado de impresión de una venta
    
    GET /panel/ventas/verificar-impresion/<venta_id>/
    
    Response:
    {
        "impreso": true/false,
        "error": true/false,
        "mensaje": "Mensaje descriptivo"
    }
    """
    
    def get(self, request, venta_id):
        try:
            # Verificar que la venta existe
            venta = get_object_or_404(Venta, pk=venta_id)
            
            # Buscar trabajos de impresión en cache para este usuario
            trabajos_key = f"trabajos_pendientes_{request.user.id}"
            trabajos_ids = cache.get(trabajos_key, [])
            
            # Buscar si hay algún trabajo de impresión tipo 'ticket' reciente
            impreso = False
            error = False
            mensaje = "Verificando estado..."
            
            # Buscar trabajos completados en los últimos 5 minutos
            for trabajo_id in trabajos_ids[:]:  # Copia de la lista
                trabajo = cache.get(f"trabajo_{trabajo_id}")
                
                if trabajo and trabajo.get('tipo') == 'ticket':
                    estado = trabajo.get('estado', 'PENDIENTE')
                    
                    if estado == 'COMPLETADO':
                        impreso = True
                        mensaje = "Ticket impreso correctamente"
                        break
                    elif estado == 'ERROR':
                        error = True
                        mensaje = trabajo.get('mensaje_resultado', 'Error al imprimir')
                        break
            
            # Si no encontramos trabajos pero han pasado más de 10 segundos, 
            # asumir que está impreso (por si el trabajo ya expiró del cache)
            tiempo_transcurrido = (timezone.now() - venta.fecha_venta).total_seconds()
            
            if not impreso and not error and tiempo_transcurrido > 10:
                # Buscar si hay registro de impresión en la BD
                try:
                    from apps.hardware_integration.models import RegistroImpresion
                    registro = RegistroImpresion.objects.filter(
                        venta=venta,
                        estado='EXITOSO'
                    ).first()
                    
                    if registro:
                        impreso = True
                        mensaje = "Ticket impreso correctamente"
                    elif tiempo_transcurrido > 30:
                        # Si han pasado más de 30 segundos sin confirmación, asumir timeout
                        error = False
                        impreso = False
                        mensaje = "No se pudo verificar el estado de impresión"
                except ImportError:
                    logger.warning("Módulo de hardware_integration no disponible")
                    impreso = True  # Asumir que se imprimió si no hay módulo
                    mensaje = "Módulo de verificación no disponible"
            
            return JsonResponse({
                'impreso': impreso,
                'error': error,
                'mensaje': mensaje
            })
            
        except Exception as e:
            logger.error(f"Error verificando estado de impresión: {e}", exc_info=True)
            return JsonResponse({
                'impreso': False,
                'error': True,
                'mensaje': f"Error del servidor: {str(e)}"
            }, status=500)


class ProcesarVentaAPIView(LoginRequiredMixin, View):
    login_url = '/login/'
    """
    Procesa una venta desde el POS (API AJAX)
    
    POST /panel/ventas/api/procesar/
    
    Body:
    {
        "items": [
            {
                "producto_id": "uuid",
                "cantidad": 5,
                "precio": 100.00,
                "descuento_porcentaje": 0,
                "es_quintal": false
            },
            {
                "producto_id": "uuid",
                "quintal_id": "uuid",
                "peso_vendido": 2.5,
                "precio": 50.00,
                "descuento_porcentaje": 10,
                "es_quintal": true
            }
        ],
        "cliente_id": "uuid" (opcional),
        "tipo_venta": "CONTADO",
        "metodo_pago": "EFECTIVO",
        "monto_recibido": 500.00,
        "observaciones": "Venta de mostrador"
    }
    
    Response:
    {
        "success": true,
        "venta_id": "uuid",
        "numero_venta": "VNT-2025-00001",
        "total": 500.00,
        "cambio": 0.00,
        "mensaje": "Venta procesada correctamente"
    }
    """
    
    def post(self, request):
        try:
            # Parsear datos del request
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
                # Convertir items si viene como string
                if isinstance(data.get('items'), str):
                    data['items'] = json.loads(data['items'])
            
            items = data.get('items', [])
            cliente_id = data.get('cliente_id')
            tipo_venta = data.get('tipo_venta', 'CONTADO')
            metodo_pago = data.get('metodo_pago', 'EFECTIVO')
            monto_recibido = Decimal(str(data.get('monto_recibido', 0)))
            observaciones = data.get('observaciones', '')
            
            # Validar que haya items
            if not items:
                return JsonResponse({
                    'success': False,
                    'error': 'El carrito está vacío'
                }, status=400)
            
            # Procesar venta dentro de transacción
            with transaction.atomic():
                from .pos.pos_service import POSService
                
                # Obtener cliente si existe
                cliente = None
                if cliente_id:
                    try:
                        cliente = Cliente.objects.get(pk=cliente_id)
                    except Cliente.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'error': 'Cliente no encontrado'
                        }, status=404)
                
                # Crear venta
                venta = POSService.crear_venta(
                    vendedor=request.user,
                    cliente=cliente,
                    tipo_venta=tipo_venta,
                    observaciones=observaciones
                )
                
                logger.info(f"🛒 Procesando venta {venta.numero_venta} con {len(items)} items")
                
                # Agregar items
                for item in items:
                    try:
                        producto = Producto.objects.get(pk=item['producto_id'])
                        
                        if item.get('es_quintal'):
                            # Item de quintal
                            quintal = Quintal.objects.get(pk=item['quintal_id'])
                            POSService.agregar_item_quintal(
                                venta=venta,
                                producto=producto,
                                quintal=quintal,
                                peso_vendido=Decimal(str(item['peso_vendido'])),
                                precio_por_unidad=Decimal(str(item['precio'])),
                                descuento_porcentaje=Decimal(str(item.get('descuento_porcentaje', 0)))
                            )
                        else:
                            # Item normal
                            POSService.agregar_item_normal(
                                venta=venta,
                                producto=producto,
                                cantidad_unidades=int(item['cantidad']),
                                precio_unitario=Decimal(str(item['precio'])),
                                descuento_porcentaje=Decimal(str(item.get('descuento_porcentaje', 0)))
                            )
                    except (Producto.DoesNotExist, Quintal.DoesNotExist) as e:
                        logger.error(f"Error agregando item: {e}")
                        return JsonResponse({
                            'success': False,
                            'error': f'Producto o quintal no encontrado: {str(e)}'
                        }, status=404)
                
                # Mapear método de pago
                if metodo_pago == 'EFECTIVO':
                    forma_pago = 'EFECTIVO'
                elif metodo_pago == 'TARJETA':
                    forma_pago = 'TARJETA_DEBITO'
                elif metodo_pago == 'TRANSFERENCIA':
                    forma_pago = 'TRANSFERENCIA'
                else:
                    forma_pago = 'EFECTIVO'
                
                # Procesar pago (usar el monto total si no se especificó monto recibido)
                monto_a_pagar = venta.total
                
                POSService.procesar_pago(
                    venta=venta,
                    forma_pago=forma_pago,
                    monto=monto_a_pagar,
                    usuario=request.user
                )
                
                # Finalizar venta (🖨️ ESTO TAMBIÉN IMPRIME AUTOMÁTICAMENTE EL TICKET)
                venta = POSService.finalizar_venta(venta)
                
                logger.info(f"✅ Venta {venta.numero_venta} procesada exitosamente - Total: ${venta.total}")
                
                return JsonResponse({
                    'success': True,
                    'venta_id': str(venta.id),
                    'numero_venta': venta.numero_venta,
                    'total': float(venta.total),
                    'cambio': float(venta.cambio),
                    'mensaje': 'Venta procesada correctamente'
                })
        
        except ValidationError as e:
            logger.warning(f"Validación fallida al procesar venta: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        
        except Exception as e:
            logger.error(f"Error procesando venta: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Error del servidor: {str(e)}'
            }, status=500)


class ReimprimirTicketView(VentasAPIAccessMixin, View):
    """
    Reimprimir ticket de una venta ya procesada
    
    POST /panel/ventas/<venta_id>/reimprimir-ticket/
    """
    
    def post(self, request, venta_id):
        try:
            venta = get_object_or_404(Venta, pk=venta_id)
            
            # Verificar que la venta esté completada
            if venta.estado != 'COMPLETADA':
                return JsonResponse({
                    'success': False,
                    'error': 'Solo se pueden reimprimir tickets de ventas completadas'
                }, status=400)
            
            # Intentar imprimir
            try:
                from apps.hardware_integration.models import Impresora
                from apps.hardware_integration.printers.ticket_printer import TicketPrinter
                from apps.hardware_integration.api.agente_views import crear_trabajo_impresion
                
                # Obtener impresora activa
                impresora = Impresora.objects.filter(
                    activa=True,
                    tipo_impresora__in=['TERMICA_FACTURA', 'TERMICA_TICKET']
                ).first()
                
                if not impresora:
                    return JsonResponse({
                        'success': False,
                        'error': 'No hay impresora activa configurada'
                    }, status=400)
                
                # Generar comandos ESC/POS
                comandos_hex = TicketPrinter.generar_comandos_ticket(venta, impresora)
                
                # Encolar trabajo de impresión
                trabajo_id = crear_trabajo_impresion(
                    usuario=request.user,
                    impresora_nombre=impresora.nombre_driver or impresora.nombre,
                    comandos_hex=comandos_hex,
                    tipo='ticket',
                    prioridad=3  # Prioridad normal para reimpresiones
                )
                
                logger.info(f"🔄 Ticket de venta {venta.numero_venta} reencolado con ID: {trabajo_id}")
                
                return JsonResponse({
                    'success': True,
                    'mensaje': 'Ticket enviado a impresora',
                    'trabajo_id': trabajo_id
                })
                
            except ImportError:
                return JsonResponse({
                    'success': False,
                    'error': 'Módulo de impresión no disponible'
                }, status=500)
            
        except Exception as e:
            logger.error(f"Error reimprimiendo ticket: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Error del servidor: {str(e)}'
            }, status=500)