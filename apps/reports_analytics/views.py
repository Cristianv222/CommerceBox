# apps/reports_analytics/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
import json
from .generators import (
    DashboardDataGenerator,
    InventoryReportGenerator,
    SalesReportGenerator,
    FinancialReportGenerator,
    TraceabilityReportGenerator
)
from .forms import (
    FiltroFechasForm,
    FiltroVentasForm,
    FiltroInventarioForm,
    FiltroFinancieroForm,
    FiltroTrazabilidadForm,
    PeriodoRapidoForm,
    ExportarReporteForm
)
from .models import ReporteGuardado, ConfiguracionReporte


# ============================================================================
# MIXINS
# ============================================================================

class ReportesAccessMixin(LoginRequiredMixin):
    """
    Mixin para verificar acceso a reportes
    Solo verifica que esté autenticado (sin permisos específicos)
    """
    pass

# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardView(ReportesAccessMixin, TemplateView):
    """
    Dashboard principal con métricas en tiempo real
    """
    template_name = 'custom_admin/reportes/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Generar dashboard
        generator = DashboardDataGenerator()
        dashboard_data = generator.generar_dashboard_completo()
        
        context['dashboard'] = dashboard_data
        context['fecha_actualizacion'] = timezone.now()
        
        return context


class DashboardActualizarView(ReportesAccessMixin, View):
    """
    Actualización AJAX del dashboard
    """
    def get(self, request):
        generator = DashboardDataGenerator()
        dashboard_data = generator.generar_dashboard_completo()
        
        return JsonResponse({
            'success': True,
            'data': dashboard_data,
            'timestamp': timezone.now().isoformat()
        })


# ============================================================================
# REPORTES DE VENTAS
# ============================================================================

class ReporteVentasView(ReportesAccessMixin, TemplateView):
    """
    Vista principal de reportes de ventas con navegación
    """
    template_name = 'custom_admin/reportes/ventas_index.html'


class VentasPeriodoView(ReportesAccessMixin, TemplateView):
    """
    Reporte general de ventas por período
    """
    template_name = 'reports/ventas/periodo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Formulario de filtros
        form = FiltroVentasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            fecha_desde = form.cleaned_data['fecha_desde']
            fecha_hasta = form.cleaned_data['fecha_hasta']
            
            # Generar reporte
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            
            # Aplicar filtros adicionales si los hay
            reporte = generator.reporte_ventas_periodo()
            
            context['reporte'] = reporte
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class VentasDiariasView(ReportesAccessMixin, TemplateView):
    """
    Ventas desglosadas por día
    """
    template_name = 'reports/ventas/diarias.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_ventas_diarias()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class ProductosMasVendidosView(ReportesAccessMixin, TemplateView):
    """
    Top productos más vendidos
    """
    template_name = 'reports/ventas/productos_top.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        limite = int(self.request.GET.get('limite', 20))
        
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_productos_mas_vendidos(limite=limite)
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class VentasCategoriasView(ReportesAccessMixin, TemplateView):
    """
    Análisis de ventas por categoría
    """
    template_name = 'reports/ventas/categorias.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_ventas_por_categoria()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class VentasVendedoresView(ReportesAccessMixin, TemplateView):
    """
    Análisis de ventas por vendedor
    """
    template_name = 'reports/ventas/vendedores.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_ventas_por_vendedor()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class ClientesTopView(ReportesAccessMixin, TemplateView):
    """
    Top clientes por volumen de compras
    """
    template_name = 'reports/ventas/clientes_top.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        limite = int(self.request.GET.get('limite', 20))
        
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_clientes_top(limite=limite)
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class DevolucionesView(ReportesAccessMixin, TemplateView):
    """
    Análisis de devoluciones
    """
    template_name = 'reports/ventas/devoluciones.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_devoluciones()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class ComparativoView(ReportesAccessMixin, TemplateView):
    """
    Comparación entre períodos
    """
    template_name = 'reports/ventas/comparativo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = SalesReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_comparativo_periodos()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


# ============================================================================
# REPORTES DE INVENTARIO
# ============================================================================

class ReporteInventarioView(ReportesAccessMixin, TemplateView):
    """
    Vista principal de reportes de inventario
    """
    template_name = 'custom_admin/reportes/inventario_index.html'


class InventarioValorizadoView(ReportesAccessMixin, TemplateView):
    """
    Inventario valorizado completo
    """
    template_name = 'reports/inventario/valorizado.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroInventarioForm(self.request.GET or None)
        context['form'] = form
        
        # Generar reporte
        generator = InventoryReportGenerator()
        reporte = generator.reporte_inventario_valorizado()
        
        # Aplicar filtros del formulario si es válido
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_producto')
            categoria = form.cleaned_data.get('categoria')
            proveedor = form.cleaned_data.get('proveedor')
            
            # Filtrar quintales
            if tipo == 'QUINTAL' or tipo == 'TODOS':
                quintales = reporte['quintales']['items']
                
                if categoria:
                    quintales = [q for q in quintales if q['categoria'] == categoria.nombre]
                if proveedor:
                    quintales = [q for q in quintales if q['proveedor'] == proveedor.nombre_comercial]
                
                reporte['quintales']['items'] = quintales
                reporte['quintales']['cantidad'] = len(quintales)
            else:
                reporte['quintales']['items'] = []
                reporte['quintales']['cantidad'] = 0
            
            # Filtrar productos normales
            if tipo == 'NORMAL' or tipo == 'TODOS':
                productos = reporte['productos_normales']['items']
                
                if categoria:
                    productos = [p for p in productos if p['categoria'] == categoria.nombre]
                
                reporte['productos_normales']['items'] = productos
                reporte['productos_normales']['cantidad'] = len(productos)
            else:
                reporte['productos_normales']['items'] = []
                reporte['productos_normales']['cantidad'] = 0
        
        context['reporte'] = reporte
        return context


class InventarioCategoriasView(ReportesAccessMixin, TemplateView):
    """
    Inventario agrupado por categoría
    """
    template_name = 'reports/inventario/categorias.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        generator = InventoryReportGenerator()
        context['reporte'] = generator.reporte_por_categoria()
        
        return context


class ProductosCriticosView(ReportesAccessMixin, TemplateView):
    """
    Productos que requieren atención inmediata
    """
    template_name = 'reports/inventario/criticos.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        generator = InventoryReportGenerator()
        context['reporte'] = generator.reporte_productos_criticos()
        
        return context


class MovimientosInventarioView(ReportesAccessMixin, TemplateView):
    """
    Historial de movimientos de inventario
    """
    template_name = 'reports/inventario/movimientos.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = InventoryReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_movimientos_inventario()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class RotacionInventarioView(ReportesAccessMixin, TemplateView):
    """
    Análisis de rotación de inventario
    """
    template_name = 'reports/inventario/rotacion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = InventoryReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_rotacion_inventario()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class InventarioProveedoresView(ReportesAccessMixin, TemplateView):
    """
    Inventario agrupado por proveedor
    """
    template_name = 'reports/inventario/proveedores.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        generator = InventoryReportGenerator()
        context['reporte'] = generator.reporte_por_proveedor()
        
        return context


# ============================================================================
# REPORTES FINANCIEROS
# ============================================================================

class ReporteFinancieroView(ReportesAccessMixin, TemplateView):
    """
    Vista principal de reportes financieros
    """
    template_name = 'custom_admin/reportes/financiero_index.html'


class MovimientosCajaView(ReportesAccessMixin, TemplateView):
    """
    Movimientos de caja del período
    """
    template_name = 'reports/financiero/movimientos_caja.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFinancieroForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            caja_id = form.cleaned_data.get('caja')
            caja_id = caja_id.id if caja_id else None
            
            generator = FinancialReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_movimientos_caja(caja_id=caja_id)
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class ArqueosCajaView(ReportesAccessMixin, TemplateView):
    """
    Análisis de arqueos de caja
    """
    template_name = 'reports/financiero/arqueos.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = FinancialReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_arqueos_caja()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class CajaChicaView(ReportesAccessMixin, TemplateView):
    """
    Análisis de caja chica
    """
    template_name = 'reports/financiero/caja_chica.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = FinancialReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_caja_chica()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class RentabilidadView(ReportesAccessMixin, TemplateView):
    """
    Análisis de rentabilidad
    """
    template_name = 'reports/financiero/rentabilidad.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = FinancialReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_rentabilidad_periodo()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class FlujoEfectivoView(ReportesAccessMixin, TemplateView):
    """
    Análisis de flujo de efectivo
    """
    template_name = 'reports/financiero/flujo_efectivo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = FinancialReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_flujo_efectivo()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


class CreditosPendientesView(ReportesAccessMixin, TemplateView):
    """
    Créditos pendientes de cobro
    """
    template_name = 'reports/financiero/creditos_pendientes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        generator = FinancialReportGenerator()
        context['reporte'] = generator.reporte_creditos_pendientes()
        
        return context


class EstadoFinancieroView(ReportesAccessMixin, TemplateView):
    """
    Estado financiero resumido
    """
    template_name = 'reports/financiero/estado_financiero.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        generator = FinancialReportGenerator()
        context['reporte'] = generator.reporte_estado_financiero()
        
        return context


# ============================================================================
# REPORTES DE TRAZABILIDAD
# ============================================================================

class TrazabilidadView(ReportesAccessMixin, TemplateView):
    """
    Vista principal de trazabilidad
    """
    template_name = 'reports/trazabilidad/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = FiltroTrazabilidadForm()
        return context


class TrazabilidadQuintalView(ReportesAccessMixin, TemplateView):
    """
    Trazabilidad completa de un quintal específico
    """
    template_name = 'reports/trazabilidad/quintal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        quintal_id = kwargs.get('quintal_id')
        generator = TraceabilityReportGenerator()
        context['reporte'] = generator.reporte_trazabilidad_quintal(quintal_id)
        
        return context


class TrazabilidadLoteView(ReportesAccessMixin, TemplateView):
    """
    Trazabilidad de un lote completo
    """
    template_name = 'reports/trazabilidad/lote.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        lote = kwargs.get('lote')
        generator = TraceabilityReportGenerator()
        context['reporte'] = generator.reporte_trazabilidad_por_lote(lote)
        
        return context


class TrazabilidadProveedorView(ReportesAccessMixin, TemplateView):
    """
    Trazabilidad de quintales de un proveedor
    """
    template_name = 'reports/trazabilidad/proveedor.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        proveedor_id = kwargs.get('proveedor_id')
        
        if form.is_valid():
            generator = TraceabilityReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_trazabilidad_por_proveedor(proveedor_id)
            context['tiene_datos'] = True
        else:
            generator = TraceabilityReportGenerator()
            context['reporte'] = generator.reporte_trazabilidad_por_proveedor(proveedor_id)
            context['tiene_datos'] = True
        
        return context


class FlujoFIFOView(ReportesAccessMixin, TemplateView):
    """
    Análisis del flujo FIFO de un producto
    """
    template_name = 'reports/trazabilidad/fifo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        producto_id = kwargs.get('producto_id')
        
        if form.is_valid():
            generator = TraceabilityReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_flujo_fifo(producto_id)
            context['tiene_datos'] = True
        else:
            generator = TraceabilityReportGenerator()
            context['reporte'] = generator.reporte_flujo_fifo(producto_id)
            context['tiene_datos'] = True
        
        return context


class CicloVidaQuintalesView(ReportesAccessMixin, TemplateView):
    """
    Análisis del ciclo de vida de quintales
    """
    template_name = 'reports/trazabilidad/ciclo_vida.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FiltroFechasForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            generator = TraceabilityReportGenerator(
                form.cleaned_data['fecha_desde'],
                form.cleaned_data['fecha_hasta']
            )
            context['reporte'] = generator.reporte_ciclo_vida_quintales()
            context['tiene_datos'] = True
        else:
            context['tiene_datos'] = False
        
        return context


# ============================================================================
# REPORTES GUARDADOS
# ============================================================================

class ReportesGuardadosView(ReportesAccessMixin, ListView):
    """
    Lista de reportes guardados
    """
    model = ReporteGuardado
    template_name = 'reports/guardados/lista.html'
    context_object_name = 'reportes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ReporteGuardado.objects.filter(
            usuario=self.request.user
        ).order_by('-fecha_generacion')
        
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_reporte=tipo)
        
        return queryset


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

class DashboardAPIView(ReportesAccessMixin, View):
    """
    API endpoint para datos del dashboard (JSON)
    Compatible con el template dashboard.html
    """
    def get(self, request):
        try:
            generator = DashboardDataGenerator()
            dashboard_data = generator.generar_dashboard_completo()
            
            # Convertir Decimal a float para JSON
            def decimal_to_float(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [decimal_to_float(item) for item in obj]
                return obj
            
            # Convertir todos los Decimales a float
            dashboard_data = decimal_to_float(dashboard_data)
            
            return JsonResponse({
                'success': True,
                'data': dashboard_data,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            import traceback
            print(f"❌ Error en Dashboard API: {e}")
            traceback.print_exc()
            
            return JsonResponse({
                'success': False,
                'error': str(e),
                'data': {
                    'resumen_ejecutivo': {
                        'ventas_dia': {'total': 0, 'cantidad': 0, 'ticket_promedio': 0},
                        'ventas_mes': {'total': 0, 'cantidad': 0},
                        'caja': {'efectivo_disponible': 0, 'estado_caja': 'CERRADA'},
                        'inventario': {'valor_total': 0}
                    },
                    'ventas': {
                        'dia': {'ventas_totales': 0, 'utilidad_bruta': 0, 'margen_porcentaje': 0},
                        'comparativa': {'variacion_porcentaje': 0}
                    },
                    'inventario': {
                        'quintales': {'valor_total': 0},
                        'productos_normales': {'valor_total': 0, 'criticos': 0, 'agotados': 0}
                    },
                    'financiero': {
                        'creditos_pendientes': {'total': 0, 'cantidad': 0}
                    },
                    'tendencias': [],
                    'ventas_por_categoria': [],
                    'top_productos': [],
                    'alertas': [],
                    'comparativas': {'variacion_porcentaje': 0}
                }
            }, status=500)


class VentasGraficoAPIView(ReportesAccessMixin, View):
    """
    API endpoint para datos de gráfico de ventas
    """
    def get(self, request):
        dias = int(request.GET.get('dias', 7))
        fecha_hasta = timezone.now().date()
        fecha_desde = fecha_hasta - timedelta(days=dias)
        
        generator = SalesReportGenerator(fecha_desde, fecha_hasta)
        reporte = generator.reporte_ventas_diarias()
        
        labels = [str(v['fecha']) for v in reporte['ventas_diarias']]
        ventas = [float(v['total_ventas']) for v in reporte['ventas_diarias']]
        
        return JsonResponse({
            'success': True,
            'data': {
                'labels': labels,
                'ventas': ventas
            }
        })


class InventarioEstadoAPIView(ReportesAccessMixin, View):
    """
    API endpoint para estado del inventario
    """
    def get(self, request):
        generator = DashboardDataGenerator()
        metricas = generator.get_metricas_inventario()
        
        return JsonResponse({
            'success': True,
            'data': metricas
        })


# ============================================================================
# DETALLE Y DESCARGA DE REPORTES GUARDADOS
# ============================================================================

class ReporteDetalleView(ReportesAccessMixin, DetailView):
    """
    Detalle de un reporte guardado
    """
    model = ReporteGuardado
    template_name = 'reports/guardados/detalle.html'
    context_object_name = 'reporte'
    pk_url_kwarg = 'reporte_id'
    
    def get_queryset(self):
        return ReporteGuardado.objects.filter(usuario=self.request.user)


class DescargarReporteView(ReportesAccessMixin, View):
    """
    Descarga de un reporte guardado
    """
    def get(self, request, reporte_id):
        reporte = get_object_or_404(
            ReporteGuardado,
            id=reporte_id,
            usuario=request.user
        )
        
        if not reporte.archivo:
            messages.error(request, 'El reporte no tiene archivo adjunto')
            return redirect('reports_analytics:reportes_guardados')
        
        response = HttpResponse(
            reporte.archivo.read(),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{reporte.nombre_archivo}"'
        
        return response


# ============================================================================
# EXPORTACIÓN DE REPORTES
# ============================================================================

class ExportarPDFView(ReportesAccessMixin, View):
    """
    Exportar reporte a PDF
    """
    def get(self, request, tipo_reporte):
        messages.info(request, 'La exportación a PDF estará disponible próximamente')
        return redirect('reports_analytics:dashboard')
    
    def post(self, request, tipo_reporte):
        messages.info(request, 'La exportación a PDF estará disponible próximamente')
        return redirect('reports_analytics:dashboard')


class ExportarExcelView(ReportesAccessMixin, View):
    """
    Exportar reporte a Excel
    """
    def get(self, request, tipo_reporte):
        messages.info(request, 'La exportación a Excel estará disponible próximamente')
        return redirect('reports_analytics:dashboard')
    
    def post(self, request, tipo_reporte):
        messages.info(request, 'La exportación a Excel estará disponible próximamente')
        return redirect('reports_analytics:dashboard')


class ExportarCSVView(ReportesAccessMixin, View):
    """
    Exportar reporte a CSV
    """
    def get(self, request, tipo_reporte):
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Columna1', 'Columna2', 'Columna3'])
        writer.writerow(['Dato1', 'Dato2', 'Dato3'])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reporte_{tipo_reporte}.csv"'
        
        return response
    
    def post(self, request, tipo_reporte):
        return self.get(request, tipo_reporte)


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

class ConfiguracionReportesView(ReportesAccessMixin, TemplateView):
    """
    Configuración de reportes
    """
    template_name = 'reports/configuracion/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        config, created = ConfiguracionReporte.objects.get_or_create(
            usuario=self.request.user
        )
        
        context['configuracion'] = config
        
        return context


class GuardarConfiguracionView(ReportesAccessMixin, View):
    """
    Guardar configuración de reportes
    """
    def post(self, request):
        config, created = ConfiguracionReporte.objects.get_or_create(
            usuario=request.user
        )
        
        messages.success(request, 'Configuración guardada correctamente')
        return redirect('reports_analytics:configuracion')


class DashboardSimpleAPIView(APIView):
    """
    API simplificado para el dashboard principal del panel
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            generator = DashboardDataGenerator()
            
            resumen = generator.get_resumen_ejecutivo()
            metricas_ventas = generator.get_metricas_ventas()
            metricas_inventario = generator.get_metricas_inventario()
            alertas = generator.get_alertas_criticas()
            top_productos = generator.get_productos_mas_vendidos(limite=5)
            tendencias = generator.get_tendencias_semanales()
            
            def decimal_to_float(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [decimal_to_float(item) for item in obj]
                return obj
            
            dashboard_data = {
                'ventas_hoy': decimal_to_float(resumen['ventas_dia']['total']),
                'num_ventas': resumen['ventas_dia']['cantidad'],
                'productos_total': metricas_inventario['productos_normales']['con_stock'] + metricas_inventario['quintales']['total_disponibles'],
                'alertas_criticas': len(alertas),
                'ventas_semana': [
                    {
                        'fecha': item['dia'].strftime('%d/%m') if hasattr(item['dia'], 'strftime') else str(item['dia']),
                        'total': decimal_to_float(item['total'])
                    }
                    for item in tendencias
                ],
                'top_productos': [
                    {
                        'nombre': item['producto__nombre'][:20],
                        'cantidad': decimal_to_float(item['total_vendido'])
                    }
                    for item in top_productos
                ],
                'ultimas_ventas': self._get_ultimas_ventas(),
                'alertas': [
                    {
                        'prioridad': alert.get('nivel', 'MEDIO'),
                        'titulo': alert.get('tipo', 'Alerta'),
                        'mensaje': alert.get('mensaje', ''),
                    }
                    for alert in alertas[:5]
                ]
            }
            
            return JsonResponse({
                'success': True,
                'data': dashboard_data,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            print(f"❌ Error en Dashboard API: {e}")
            import traceback
            traceback.print_exc()
            
            return JsonResponse({
                'success': False,
                'error': str(e),
                'data': {
                    'ventas_hoy': 0,
                    'num_ventas': 0,
                    'productos_total': 0,
                    'alertas_criticas': 0,
                    'ventas_semana': [],
                    'top_productos': [],
                    'ultimas_ventas': [],
                    'alertas': []
                }
            }, status=500)
    
    def _get_ultimas_ventas(self):
        try:
            from apps.sales_management.models import Venta
            
            ultimas = Venta.objects.filter(
                estado='COMPLETADA'
            ).select_related('cliente').order_by('-fecha_venta')[:5]
            
            return [
                {
                    'numero_venta': venta.numero_venta,
                    'cliente': venta.cliente.nombre_completo() if venta.cliente else 'Público General',
                    'total': float(venta.total),
                    'estado': venta.estado
                }
                for venta in ultimas
            ]
        except Exception as e:
            print(f"Error obteniendo últimas ventas: {e}")
            return []


# ============================================================================
# 🆕 API ENDPOINTS PARA DASHBOARD DE VENTAS COMPLETO
# ============================================================================

class VentasPeriodoAPIView(ReportesAccessMixin, View):
    """API: Ventas por período"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_ventas_periodo()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class VentasDiariasAPIView(ReportesAccessMixin, View):
    """API: Ventas diarias"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_ventas_diarias()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class ProductosTopAPIView(ReportesAccessMixin, View):
    """API: Top productos"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_productos_mas_vendidos(limite=20)
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class CategoriasAPIView(ReportesAccessMixin, View):
    """API: Categorías"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_ventas_por_categoria()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class VendedoresAPIView(ReportesAccessMixin, View):
    """API: Vendedores"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_ventas_por_vendedor()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class ClientesTopAPIView(ReportesAccessMixin, View):
    """API: Top clientes"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_clientes_top(limite=20)
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class HorariosAPIView(ReportesAccessMixin, View):
    """API: Horarios"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_horarios_ventas()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class DevolucionesAPIView(ReportesAccessMixin, View):
    """API: Devoluciones"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_devoluciones()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class ComparativoAPIView(ReportesAccessMixin, View):
    """API: Comparativo"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_comparativo_periodos()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class MargenesAPIView(ReportesAccessMixin, View):
    """API: Márgenes"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = SalesReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_analisis_margenes()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj


class DashboardVentasCompletView(ReportesAccessMixin, TemplateView):
    """Vista del dashboard completo de ventas"""
    template_name = 'reports/ventas/dashboard_ventas.html'
# ============================================================================
# 🆕 API ENDPOINTS - DASHBOARD DE INVENTARIO COMPLETO
# ============================================================================

class InventarioValorizadoAPIView(ReportesAccessMixin, View):
    """API: Inventario valorizado"""
    def get(self, request):
        try:
            generator = InventoryReportGenerator()
            data = generator.reporte_inventario_valorizado()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class InventarioCategoriasAPIView(ReportesAccessMixin, View):
    """API: Inventario por categorías"""
    def get(self, request):
        try:
            generator = InventoryReportGenerator()
            data = generator.reporte_por_categoria()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class ProductosCriticosAPIView(ReportesAccessMixin, View):
    """API: Productos críticos"""
    def get(self, request):
        try:
            generator = InventoryReportGenerator()
            data = generator.reporte_productos_criticos()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class MovimientosInventarioAPIView(ReportesAccessMixin, View):
    """API: Movimientos de inventario"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = InventoryReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_movimientos_inventario()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class RotacionInventarioAPIView(ReportesAccessMixin, View):
    """API: Rotación de inventario"""
    def get(self, request):
        try:
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            
            if fecha_desde and fecha_hasta:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            else:
                fecha_hasta = timezone.now().date()
                fecha_desde = fecha_hasta - timedelta(days=30)
            
            generator = InventoryReportGenerator(fecha_desde, fecha_hasta)
            data = generator.reporte_rotacion_inventario()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class InventarioProveedoresAPIView(ReportesAccessMixin, View):
    """API: Inventario por proveedores"""
    def get(self, request):
        try:
            generator = InventoryReportGenerator()
            data = generator.reporte_por_proveedor()
            data = self._convert_decimals(data)
            
            return JsonResponse(data)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj


class DashboardInventarioCompletView(ReportesAccessMixin, TemplateView):
    """Vista del dashboard completo de inventario"""
    template_name = 'reports/inventario/dashboard_inventario.html'