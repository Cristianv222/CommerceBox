# apps/financial_management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta, datetime
from django.db.models.functions import Coalesce, TruncDate
from apps.financial_management import apps
from apps.sales_management.models import DetalleVenta, Cliente, Venta
import json
from django.db.models import Avg
from .models import (
    Caja, MovimientoCaja, ArqueoCaja,
    CajaChica, MovimientoCajaChica, CuentaPorCobrar, PagoCuentaPorCobrar, CuentaPorPagar, PagoCuentaPorPagar,
    CuentaPorPagar, ReporteCuentasPorPagar
)
from .forms import (
    CajaForm, AperturaCajaForm, CierreCajaForm, MovimientoCajaForm,
    CajaChicaForm, GastoCajaChicaForm, ReposicionCajaChicaForm,
    BuscarMovimientosForm, CuentaPorCobrarForm, RegistrarPagoCuentaPorCobrarForm, BuscarCuentasPorCobrarForm,
    CuentaPorPagarForm, RegistrarPagoCuentaPorPagarForm, BuscarCuentasPorPagarForm
)
from .mixins import (
    FinancialAccessMixin, CajaEditMixin, CajeroAccessMixin,
    SupervisorAccessMixin, CajaChicaAccessMixin, FormMessagesMixin, CreditoAccessMixin
)
from apps.inventory_management.models import Proveedor

# ============================================================================
# DASHBOARD FINANCIERO
# ============================================================================

class FinancialDashboardView(FinancialAccessMixin, TemplateView):
    """Dashboard principal del módulo financiero con utilidades"""
    template_name = 'custom_admin/financial/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        cajas_abiertas = Caja.objects.filter(estado='ABIERTA', activa=True).select_related('cajero_actual')
        context['cajas_abiertas'] = cajas_abiertas
        context['total_cajas_abiertas'] = cajas_abiertas.count()
        context['total_efectivo_cajas'] = cajas_abiertas.aggregate(total=Sum('monto_actual'))['total'] or Decimal('0')
        
        ventas_hoy = MovimientoCaja.objects.filter(tipo_movimiento='VENTA', fecha_movimiento__gte=hoy_inicio).aggregate(total=Sum('monto'), cantidad=Count('id'))
        context['ventas_hoy'] = ventas_hoy['total'] or Decimal('0')
        context['cantidad_ventas_hoy'] = ventas_hoy['cantidad'] or 0
        
        detalles_hoy = DetalleVenta.objects.filter(venta__fecha_venta__date=hoy, venta__estado='COMPLETADA').aggregate(ventas=Coalesce(Sum('total'), Decimal('0')), costos=Coalesce(Sum('costo_total'), Decimal('0')))
        utilidad_hoy = detalles_hoy['ventas'] - detalles_hoy['costos']
        margen_hoy = (utilidad_hoy / detalles_hoy['ventas'] * 100) if detalles_hoy['ventas'] > 0 else Decimal('0')
        context['utilidad_dia'] = utilidad_hoy.quantize(Decimal('0.01'))
        context['margen_dia'] = margen_hoy.quantize(Decimal('0.01'))
        
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        detalles_semana = DetalleVenta.objects.filter(venta__fecha_venta__date__gte=inicio_semana, venta__fecha_venta__date__lte=hoy, venta__estado='COMPLETADA').aggregate(ventas=Coalesce(Sum('total'), Decimal('0')), costos=Coalesce(Sum('costo_total'), Decimal('0')))
        utilidad_semana = detalles_semana['ventas'] - detalles_semana['costos']
        margen_semana = (utilidad_semana / detalles_semana['ventas'] * 100) if detalles_semana['ventas'] > 0 else Decimal('0')
        context['ventas_semana'] = detalles_semana['ventas'].quantize(Decimal('0.01'))
        context['costos_semana'] = detalles_semana['costos'].quantize(Decimal('0.01'))
        context['utilidad_semana'] = utilidad_semana.quantize(Decimal('0.01'))
        context['margen_semana'] = margen_semana.quantize(Decimal('0.01'))
        
        inicio_mes = hoy.replace(day=1)
        detalles_mes = DetalleVenta.objects.filter(venta__fecha_venta__date__gte=inicio_mes, venta__fecha_venta__date__lte=hoy, venta__estado='COMPLETADA').aggregate(ventas=Coalesce(Sum('total'), Decimal('0')), costos=Coalesce(Sum('costo_total'), Decimal('0')))
        utilidad_mes = detalles_mes['ventas'] - detalles_mes['costos']
        margen_mes = (utilidad_mes / detalles_mes['ventas'] * 100) if detalles_mes['ventas'] > 0 else Decimal('0')
        context['ventas_mes'] = detalles_mes['ventas'].quantize(Decimal('0.01'))
        context['costos_mes'] = detalles_mes['costos'].quantize(Decimal('0.01'))
        context['utilidad_mes'] = utilidad_mes.quantize(Decimal('0.01'))
        context['margen_mes'] = margen_mes.quantize(Decimal('0.01'))
        
        hace_7_dias = hoy - timedelta(days=6)
        ventas_diarias = DetalleVenta.objects.filter(venta__fecha_venta__date__gte=hace_7_dias, venta__fecha_venta__date__lte=hoy, venta__estado='COMPLETADA').annotate(dia=TruncDate('venta__fecha_venta')).values('dia').annotate(ventas=Coalesce(Sum('total'), Decimal('0')), costos=Coalesce(Sum('costo_total'), Decimal('0'))).order_by('dia')
        
        tendencia_labels = []
        tendencia_data = []
        for i in range(7):
            dia = hace_7_dias + timedelta(days=i)
            dia_data = next((item for item in ventas_diarias if item['dia'] == dia), {'ventas': Decimal('0'), 'costos': Decimal('0')})
            utilidad = dia_data['ventas'] - dia_data['costos']
            tendencia_labels.append(dia.strftime('%d/%m'))
            tendencia_data.append(float(utilidad))
        
        context['tendencia_labels'] = json.dumps(tendencia_labels)
        context['tendencia_data'] = json.dumps(tendencia_data)
        
        cajas_chicas = CajaChica.objects.filter(estado='ACTIVA').select_related('responsable')
        context['cajas_chicas'] = cajas_chicas
        context['cajas_chicas_criticas'] = cajas_chicas.filter(monto_actual__lte=F('umbral_reposicion')).count()
        context['gastos_caja_chica_hoy'] = MovimientoCajaChica.objects.filter(tipo_movimiento='GASTO', fecha_movimiento__date=hoy).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        context['ultimos_movimientos'] = MovimientoCaja.objects.filter(fecha_movimiento__gte=hoy_inicio).select_related('caja', 'usuario', 'venta').order_by('-fecha_movimiento')[:10]
        
        for caja in cajas_abiertas:
            caja.ventas_dia = MovimientoCaja.objects.filter(caja=caja, tipo_movimiento='VENTA', fecha_movimiento__gte=hoy_inicio).count()
        
        return context


# ============================================================================
# GESTIÓN DE CAJAS
# ============================================================================

class CajaListView(CajaEditMixin, ListView):
    """Lista de cajas del sistema"""
    model = Caja
    template_name = 'financial/caja_list.html'
    context_object_name = 'cajas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset.order_by('-fecha_apertura')


class CajaCreateView(CajaEditMixin, FormMessagesMixin, CreateView):
    """Crear nueva caja"""
    model = Caja
    form_class = CajaForm
    template_name = 'financial/caja_form.html'
    success_url = reverse_lazy('financial_management:caja_list')
    success_message = "Caja '{object.nombre}' creada exitosamente."


class CajaDetailView(FinancialAccessMixin, DetailView):
    """Detalle de caja con movimientos"""
    model = Caja
    template_name = 'financial/caja_detail.html'
    context_object_name = 'caja'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja = self.get_object()
        
        # Movimientos de la caja
        movimientos = MovimientoCaja.objects.filter(
            caja=caja
        ).select_related('usuario', 'venta').order_by('-fecha_movimiento')
        
        # Filtrar por fecha si se proporciona
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if fecha_desde:
            movimientos = movimientos.filter(
                fecha_movimiento__gte=fecha_desde
            )
        if fecha_hasta:
            movimientos = movimientos.filter(
                fecha_movimiento__lte=fecha_hasta
            )
        
        context['movimientos'] = movimientos[:50]
        
        # Estadísticas de hoy
        if caja.estado == 'ABIERTA':
            hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            context['ventas_hoy'] = MovimientoCaja.objects.filter(
                caja=caja,
                tipo_movimiento='VENTA',
                fecha_movimiento__gte=hoy_inicio
            ).aggregate(
                total=Sum('monto'),
                cantidad=Count('id')
            )
            
            context['ingresos_hoy'] = MovimientoCaja.objects.filter(
                caja=caja,
                tipo_movimiento='INGRESO',
                fecha_movimiento__gte=hoy_inicio
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
            
            context['retiros_hoy'] = MovimientoCaja.objects.filter(
                caja=caja,
                tipo_movimiento='RETIRO',
                fecha_movimiento__gte=hoy_inicio
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        # Formulario de búsqueda
        context['buscar_form'] = BuscarMovimientosForm(self.request.GET)
        
        return context


class CajaUpdateView(CajaEditMixin, FormMessagesMixin, UpdateView):
    """Editar caja"""
    model = Caja
    form_class = CajaForm
    template_name = 'financial/caja_form.html'
    success_message = "Caja '{object.nombre}' actualizada exitosamente."
    
    def get_success_url(self):
        return reverse('financial_management:caja_detail', kwargs={'pk': self.object.pk})


# ============================================================================
# APERTURA Y CIERRE DE CAJA
# ============================================================================

class AperturaCajaView(CajeroAccessMixin, TemplateView):
    """Vista para abrir caja"""
    template_name = 'financial/caja_apertura.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja = get_object_or_404(Caja, pk=self.kwargs['pk'])
        
        if caja.estado == 'ABIERTA':
            messages.warning(self.request, "Esta caja ya está abierta.")
            return redirect('financial_management:caja_detail', pk=caja.pk)
        
        context['caja'] = caja
        context['form'] = AperturaCajaForm(caja=caja)
        return context
    
    @transaction.atomic
    def post(self, request, pk):
        caja = get_object_or_404(Caja, pk=pk)
        form = AperturaCajaForm(request.POST, caja=caja)
        
        if form.is_valid():
            try:
                monto_apertura = form.cleaned_data['monto_apertura']
                caja.abrir_caja(request.user, monto_apertura)
                
                messages.success(
                    request,
                    f"Caja {caja.nombre} abierta exitosamente con ${monto_apertura}"
                )
                return redirect('financial_management:caja_detail', pk=caja.pk)
            
            except ValueError as e:
                messages.error(request, str(e))
        
        return render(request, self.template_name, {
            'caja': caja,
            'form': form
        })


class CierreCajaView(CajeroAccessMixin, TemplateView):
    """Vista para cerrar caja y realizar arqueo"""
    template_name = 'financial/caja_cierre.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja = get_object_or_404(Caja, pk=self.kwargs['pk'])
        
        if caja.estado == 'CERRADA':
            messages.warning(self.request, "Esta caja ya está cerrada.")
            return redirect('financial_management:caja_detail', pk=caja.pk)
        
        # Calcular resumen de la sesión
        hoy_inicio = caja.fecha_apertura
        
        movimientos_sesion = MovimientoCaja.objects.filter(
            caja=caja,
            fecha_movimiento__gte=hoy_inicio
        )
        
        context['caja'] = caja
        context['form'] = CierreCajaForm(caja=caja)
        
        # Resumen de movimientos
        context['total_ventas'] = movimientos_sesion.filter(
            tipo_movimiento='VENTA'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        context['total_ingresos'] = movimientos_sesion.filter(
            tipo_movimiento='INGRESO'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        context['total_retiros'] = movimientos_sesion.filter(
            tipo_movimiento='RETIRO'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        context['monto_esperado'] = caja.monto_actual
        
        return context
    
    @transaction.atomic
    def post(self, request, pk):
        caja = get_object_or_404(Caja, pk=pk)
        form = CierreCajaForm(request.POST, caja=caja)
        
        if form.is_valid():
            try:
                # Datos del formulario
                monto_contado = form.cleaned_data['monto_contado']
                
                # Cerrar caja
                diferencia = caja.cerrar_caja(request.user, monto_contado)
                
                # Crear arqueo
                hoy_inicio = caja.fecha_apertura
                movimientos_sesion = MovimientoCaja.objects.filter(
                    caja=caja,
                    fecha_movimiento__gte=hoy_inicio
                )
                
                # Generar número de arqueo
                ultimo_arqueo = ArqueoCaja.objects.order_by('-numero_arqueo').first()
                if ultimo_arqueo:
                    numero = int(ultimo_arqueo.numero_arqueo.split('-')[-1]) + 1
                else:
                    numero = 1
                numero_arqueo = f"ARQ-{timezone.now().year}-{numero:05d}"
                
                arqueo = ArqueoCaja.objects.create(
                    numero_arqueo=numero_arqueo,
                    caja=caja,
                    fecha_apertura=hoy_inicio,
                    fecha_cierre=timezone.now(),
                    monto_apertura=caja.monto_apertura,
                    total_ventas=movimientos_sesion.filter(
                        tipo_movimiento='VENTA'
                    ).aggregate(total=Sum('monto'))['total'] or Decimal('0'),
                    total_ingresos=movimientos_sesion.filter(
                        tipo_movimiento='INGRESO'
                    ).aggregate(total=Sum('monto'))['total'] or Decimal('0'),
                    total_retiros=movimientos_sesion.filter(
                        tipo_movimiento='RETIRO'
                    ).aggregate(total=Sum('monto'))['total'] or Decimal('0'),
                    monto_esperado=caja.monto_actual + monto_contado,  # Antes de cerrar
                    monto_contado=monto_contado,
                    billetes_100=form.cleaned_data['billetes_100'],
                    billetes_50=form.cleaned_data['billetes_50'],
                    billetes_20=form.cleaned_data['billetes_20'],
                    billetes_10=form.cleaned_data['billetes_10'],
                    billetes_5=form.cleaned_data['billetes_5'],
                    billetes_1=form.cleaned_data['billetes_1'],
                    monedas=form.cleaned_data['monedas'],
                    diferencia=diferencia,
                    observaciones=form.cleaned_data['observaciones'],
                    observaciones_diferencia=form.cleaned_data['observaciones_diferencia'],
                    usuario_apertura=caja.usuario_apertura,
                    usuario_cierre=request.user
                )
                
                # Mensaje según resultado
                if arqueo.estado == 'CUADRADO':
                    messages.success(request, f"✅ Caja cerrada correctamente. Arqueo: {arqueo.numero_arqueo}")
                elif arqueo.estado == 'SOBRANTE':
                    messages.warning(
                        request,
                        f"➕ Caja cerrada con sobrante de ${abs(diferencia)}. Arqueo: {arqueo.numero_arqueo}"
                    )
                else:
                    messages.error(
                        request,
                        f"➖ Caja cerrada con faltante de ${abs(diferencia)}. Arqueo: {arqueo.numero_arqueo}"
                    )
                
                return redirect('financial_management:arqueo_detail', pk=arqueo.pk)
            
            except ValueError as e:
                messages.error(request, str(e))
        
        return render(request, self.template_name, self.get_context_data())


# ============================================================================
# MOVIMIENTOS DE CAJA
# ============================================================================

class RegistrarMovimientoView(CajeroAccessMixin, TemplateView):
    """Registrar ingreso/retiro en caja"""
    template_name = 'financial/movimiento_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja = get_object_or_404(Caja, pk=self.kwargs['pk'])
        
        if caja.estado != 'ABIERTA':
            messages.error(self.request, "La caja debe estar abierta para registrar movimientos.")
            return redirect('financial_management:caja_detail', pk=caja.pk)
        
        context['caja'] = caja
        context['form'] = MovimientoCajaForm()
        return context
    
    @transaction.atomic
    def post(self, request, pk):
        caja = get_object_or_404(Caja, pk=pk)
        form = MovimientoCajaForm(request.POST)
        
        if form.is_valid():
            tipo_movimiento = form.cleaned_data['tipo_movimiento']
            monto = form.cleaned_data['monto']
            descripcion = form.cleaned_data['descripcion']
            
            # Crear movimiento
            MovimientoCaja.objects.create(
                caja=caja,
                tipo_movimiento=tipo_movimiento,
                monto=monto,
                descripcion=descripcion,
                saldo_anterior=caja.monto_actual,
                saldo_nuevo=caja.monto_actual + monto if tipo_movimiento == 'INGRESO' else caja.monto_actual - monto,
                usuario=request.user
            )
            
            # Actualizar saldo de la caja
            if tipo_movimiento == 'INGRESO':
                caja.monto_actual += monto
            else:  # RETIRO
                caja.monto_actual -= monto
            caja.save()
            
            messages.success(request, f"Movimiento de {tipo_movimiento} registrado exitosamente.")
            return redirect('financial_management:caja_detail', pk=caja.pk)
        
        return render(request, self.template_name, {
            'caja': caja,
            'form': form
        })


# ============================================================================
# ARQUEOS
# ============================================================================

class ArqueoListView(FinancialAccessMixin, ListView):
    """Lista de arqueos realizados"""
    model = ArqueoCaja
    template_name = 'financial/arqueo_list.html'
    context_object_name = 'arqueos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'caja', 'usuario_apertura', 'usuario_cierre'
        )
        
        # Filtros
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        caja_id = self.request.GET.get('caja')
        if caja_id:
            queryset = queryset.filter(caja_id=caja_id)
        
        return queryset.order_by('-fecha_cierre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cajas'] = Caja.objects.all()
        return context


class ArqueoDetailView(FinancialAccessMixin, DetailView):
    """Detalle de un arqueo"""
    model = ArqueoCaja
    template_name = 'financial/arqueo_detail.html'
    context_object_name = 'arqueo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arqueo = self.get_object()
        
        # Movimientos del período
        context['movimientos'] = MovimientoCaja.objects.filter(
            caja=arqueo.caja,
            fecha_movimiento__gte=arqueo.fecha_apertura,
            fecha_movimiento__lte=arqueo.fecha_cierre
        ).select_related('usuario').order_by('fecha_movimiento')
        
        return context


# ============================================================================
# CAJA CHICA
# ============================================================================

class CajaChicaListView(CajaChicaAccessMixin, ListView):
    """Lista de cajas chicas"""
    model = CajaChica
    template_name = 'financial_management/caja_chica_list.html'
    context_object_name = 'cajas_chicas'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('responsable')
        
        # Si no es admin/supervisor, solo ver las que es responsable
        if self.request.user.rol not in ['ADMIN', 'SUPERVISOR']:
            queryset = queryset.filter(responsable=self.request.user)
        
        return queryset.order_by('codigo')


class CajaChicaCreateView(SupervisorAccessMixin, FormMessagesMixin, CreateView):
    """Crear nueva caja chica"""
    model = CajaChica
    form_class = CajaChicaForm
    template_name = 'financial/caja_chica_form.html'
    success_url = reverse_lazy('financial_management:caja_chica_list')
    success_message = "Caja chica '{object.nombre}' creada exitosamente."
    
    def form_valid(self, form):
        # El monto actual inicial es igual al fondo
        form.instance.monto_actual = form.instance.monto_fondo
        return super().form_valid(form)


class CajaChicaDetailView(CajaChicaAccessMixin, DetailView):
    """Detalle de caja chica con movimientos"""
    model = CajaChica
    template_name = 'financial/caja_chica_detail.html'
    context_object_name = 'caja_chica'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja_chica = self.get_object()
        
        # Verificar acceso
        if (self.request.user.rol not in ['ADMIN', 'SUPERVISOR'] and
            caja_chica.responsable != self.request.user):
            messages.error(self.request, "No tienes acceso a esta caja chica.")
            return redirect('financial_management:caja_chica_list')
        
        # Movimientos
        movimientos = MovimientoCajaChica.objects.filter(
            caja_chica=caja_chica
        ).select_related('usuario').order_by('-fecha_movimiento')
        
        # Filtrar por fecha si se proporciona
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if fecha_desde:
            movimientos = movimientos.filter(
                fecha_movimiento__gte=fecha_desde
            )
        if fecha_hasta:
            movimientos = movimientos.filter(
                fecha_movimiento__lte=fecha_hasta
            )
        
        context['movimientos'] = movimientos[:50]
        
        # Estadísticas del mes actual
        primer_dia_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        gastos_mes = MovimientoCajaChica.objects.filter(
            caja_chica=caja_chica,
            tipo_movimiento='GASTO',
            fecha_movimiento__gte=primer_dia_mes
        )
        
        context['gastos_mes'] = gastos_mes.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')
        
        context['cantidad_gastos_mes'] = gastos_mes.count()
        
        # Gastos por categoría del mes
        context['gastos_por_categoria'] = gastos_mes.values(
            'categoria_gasto'
        ).annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        ).order_by('-total')
        
        return context


class CajaChicaUpdateView(SupervisorAccessMixin, FormMessagesMixin, UpdateView):
    """Editar caja chica"""
    model = CajaChica
    form_class = CajaChicaForm
    template_name = 'financial/caja_chica_form.html'
    success_message = "Caja chica '{object.nombre}' actualizada exitosamente."
    
    def get_success_url(self):
        return reverse('financial_management:caja_chica_detail', kwargs={'pk': self.object.pk})


class RegistrarGastoCajaChicaView(CajaChicaAccessMixin, TemplateView):
    """Registrar un gasto de caja chica"""
    template_name = 'financial/gasto_caja_chica_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja_chica = get_object_or_404(CajaChica, pk=self.kwargs['pk'])
        
        # Verificar acceso
        if (self.request.user.rol not in ['ADMIN', 'SUPERVISOR'] and
            caja_chica.responsable != self.request.user):
            messages.error(self.request, "No tienes acceso a esta caja chica.")
            return redirect('financial_management:caja_chica_list')
        
        if caja_chica.estado != 'ACTIVA':
            messages.error(self.request, "Esta caja chica no está activa.")
            return redirect('financial_management:caja_chica_detail', pk=caja_chica.pk)
        
        context['caja_chica'] = caja_chica
        context['form'] = GastoCajaChicaForm(caja_chica=caja_chica)
        return context
    
    @transaction.atomic
    def post(self, request, pk):
        caja_chica = get_object_or_404(CajaChica, pk=pk)
        form = GastoCajaChicaForm(
            request.POST,
            request.FILES,
            caja_chica=caja_chica
        )
        
        if form.is_valid():
            try:
                categoria = form.cleaned_data['categoria_gasto']
                monto = form.cleaned_data['monto']
                descripcion = form.cleaned_data['descripcion']
                numero_comprobante = form.cleaned_data.get('numero_comprobante', '')
                comprobante_adjunto = form.cleaned_data.get('comprobante_adjunto')
                
                # Registrar gasto
                caja_chica.registrar_gasto(
                    monto=monto,
                    categoria=categoria,
                    descripcion=descripcion,
                    usuario=request.user
                )
                
                # Actualizar último movimiento con datos adicionales
                ultimo_movimiento = MovimientoCajaChica.objects.filter(
                    caja_chica=caja_chica
                ).order_by('-fecha_movimiento').first()
                
                if ultimo_movimiento:
                    ultimo_movimiento.numero_comprobante = numero_comprobante
                    ultimo_movimiento.comprobante_adjunto = comprobante_adjunto
                    ultimo_movimiento.save()
                
                messages.success(
                    request,
                    f"Gasto de ${monto} registrado exitosamente. Saldo: ${caja_chica.monto_actual}"
                )
                
                # Alerta si necesita reposición
                if caja_chica.necesita_reposicion():
                    messages.warning(
                        request,
                        f"⚠️ La caja chica necesita reposición de ${caja_chica.monto_a_reponer()}"
                    )
                
                return redirect('financial_management:caja_chica_detail', pk=caja_chica.pk)
            
            except ValueError as e:
                messages.error(request, str(e))
        
        return render(request, self.template_name, {
            'caja_chica': caja_chica,
            'form': form
        })


class ReponerCajaChicaView(SupervisorAccessMixin, TemplateView):
    """Reposición de fondo de caja chica"""
    template_name = 'financial/reposicion_caja_chica_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja_chica = get_object_or_404(CajaChica, pk=self.kwargs['pk'])
        context['caja_chica'] = caja_chica
        context['form'] = ReposicionCajaChicaForm(caja_chica=caja_chica)
        return context

    @transaction.atomic
    def post(self, request, pk):
        caja_chica = get_object_or_404(CajaChica, pk=pk)
        form = ReposicionCajaChicaForm(request.POST, caja_chica=caja_chica)
        
        if form.is_valid():
            monto = form.cleaned_data['monto']
            observaciones = form.cleaned_data.get('observaciones', '')
            
            # Reponer fondo
            caja_chica.reponer_fondo(monto, request.user)
            
            # Actualizar observaciones del último movimiento
            if observaciones:
                ultimo_movimiento = MovimientoCajaChica.objects.filter(
                    caja_chica=caja_chica
                ).order_by('-fecha_movimiento').first()
                
                if ultimo_movimiento:
                    ultimo_movimiento.descripcion += f"\n{observaciones}"
                    ultimo_movimiento.save()
            
            messages.success(
                request,
                f"Fondo de caja chica repuesto con ${monto}. Nuevo saldo: ${caja_chica.monto_actual}"
            )
            return redirect('financial_management:caja_chica_detail', pk=caja_chica.pk)
        
        return render(request, self.template_name, self.get_context_data())


# ============================================================================
# REPORTES Y CONSULTAS
# ============================================================================

class ReporteFinancieroView(SupervisorAccessMixin, TemplateView):
    """Reporte financiero general"""
    template_name = 'financial/reporte_financiero.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener rango de fechas
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if not fecha_desde:
            fecha_desde = timezone.now().replace(day=1).date()
        else:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        
        if not fecha_hasta:
            fecha_hasta = timezone.now().date()
        else:
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
        
        context['fecha_desde'] = fecha_desde
        context['fecha_hasta'] = fecha_hasta
        
        # Movimientos de caja en el período
        movimientos = MovimientoCaja.objects.filter(
            fecha_movimiento__date__gte=fecha_desde,
            fecha_movimiento__date__lte=fecha_hasta
        )
        
        # Ventas del período
        context['ventas_periodo'] = movimientos.filter(
            tipo_movimiento='VENTA'
        ).aggregate(
            total=Sum('monto'),
            cantidad=Count('id')
        )
        
        # Ingresos y retiros
        context['ingresos_periodo'] = movimientos.filter(
            tipo_movimiento__in=['INGRESO', 'AJUSTE_POSITIVO']
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        context['retiros_periodo'] = movimientos.filter(
            tipo_movimiento__in=['RETIRO', 'AJUSTE_NEGATIVO']
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        # Gastos de caja chica del período
        gastos_caja_chica = MovimientoCajaChica.objects.filter(
            tipo_movimiento='GASTO',
            fecha_movimiento__date__gte=fecha_desde,
            fecha_movimiento__date__lte=fecha_hasta
        )
        
        context['gastos_caja_chica'] = gastos_caja_chica.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')
        
        context['gastos_por_categoria'] = gastos_caja_chica.values(
            'categoria_gasto'
        ).annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        ).order_by('-total')
        
        # Arqueos del período
        context['arqueos'] = ArqueoCaja.objects.filter(
            fecha_cierre__date__gte=fecha_desde,
            fecha_cierre__date__lte=fecha_hasta
        ).select_related('caja', 'usuario_cierre')
        
        # Resumen de arqueos
        context['arqueos_cuadrados'] = context['arqueos'].filter(
            estado='CUADRADO'
        ).count()
        context['arqueos_con_diferencia'] = context['arqueos'].exclude(
            estado='CUADRADO'
        ).count()
        
        return context


# ============================================================================
# APIS Y UTILIDADES
# ============================================================================

class EstadoCajaAPIView(FinancialAccessMixin, View):
    """API para obtener el estado actual de una caja"""
    
    def get(self, request, pk):
        caja = get_object_or_404(Caja, pk=pk)
        
        data = {
            'id': str(caja.id),
            'nombre': caja.nombre,
            'codigo': caja.codigo,
            'estado': caja.estado,
            'monto_actual': float(caja.monto_actual),
            'fecha_apertura': caja.fecha_apertura.isoformat() if caja.fecha_apertura else None,
        }
        
        if caja.estado == 'ABIERTA':
            # Ventas de hoy
            hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            ventas_hoy = MovimientoCaja.objects.filter(
                caja=caja,
                tipo_movimiento='VENTA',
                fecha_movimiento__gte=hoy_inicio
            ).aggregate(
                total=Sum('monto'),
                cantidad=Count('id')
            )
            
            data['ventas_hoy'] = {
                'total': float(ventas_hoy['total'] or 0),
                'cantidad': ventas_hoy['cantidad'] or 0
            }
        
        return JsonResponse(data)


class CajaChicaEstadoAPIView(CajaChicaAccessMixin, View):
    """API para obtener el estado de una caja chica"""
    
    def get(self, request, pk):
        caja_chica = get_object_or_404(CajaChica, pk=pk)
        
        data = {
            'id': str(caja_chica.id),
            'nombre': caja_chica.nombre,
            'codigo': caja_chica.codigo,
            'monto_fondo': float(caja_chica.monto_fondo),
            'monto_actual': float(caja_chica.monto_actual),
            'porcentaje_disponible': float((caja_chica.monto_actual / caja_chica.monto_fondo * 100) if caja_chica.monto_fondo > 0 else 0),
            'necesita_reposicion': caja_chica.necesita_reposicion(),
            'monto_a_reponer': float(caja_chica.monto_a_reponer()),
        }
        
        return JsonResponse(data)
    # ============================================================================
# CUENTAS POR COBRAR (CRÉDITOS A CLIENTES)
# ============================================================================

class CuentaPorCobrarListView(CreditoAccessMixin, ListView):
    """Lista de cuentas por cobrar (créditos a clientes)"""
    model = CuentaPorCobrar
    template_name = 'custom_admin/finanzas/cuenta_por_cobrar_list.html'
    context_object_name = 'cuentas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CuentaPorCobrar.objects.select_related(
            'cliente', 'venta', 'usuario_registro'
        ).order_by('-fecha_emision')
        
        # Aplicar filtros del formulario
        form = BuscarCuentasPorCobrarForm(self.request.GET)
        
        if form.is_valid():
            cliente = form.cleaned_data.get('cliente')
            if cliente:
                queryset = queryset.filter(
                    Q(cliente__nombres__icontains=cliente) |
                    Q(cliente__apellidos__icontains=cliente) |
                    Q(cliente__numero_documento__icontains=cliente)  # ✅ CORRECCIÓN
                )
            
            estado = form.cleaned_data.get('estado')
            if estado:
                queryset = queryset.filter(estado=estado)
            
            fecha_desde = form.cleaned_data.get('fecha_desde')
            if fecha_desde:
                queryset = queryset.filter(fecha_emision__gte=fecha_desde)
            
            fecha_hasta = form.cleaned_data.get('fecha_hasta')
            if fecha_hasta:
                queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
            
            solo_vencidas = form.cleaned_data.get('solo_vencidas')
            if solo_vencidas:
                queryset = queryset.filter(estado='VENCIDA')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Formulario de búsqueda
        context['buscar_form'] = BuscarCuentasPorCobrarForm(self.request.GET)
        
        # Estadísticas generales
        from .models import ReporteCuentasPorCobrar
        context['resumen'] = ReporteCuentasPorCobrar.resumen_general()
        
        # Totales filtrados
        cuentas_filtradas = self.get_queryset()
        context['total_filtrado'] = cuentas_filtradas.aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        context['cantidad_filtrada'] = cuentas_filtradas.count()
        
        return context




class CuentaPorCobrarCreateView(CreditoAccessMixin, View):
    """Crear nueva cuenta por cobrar vía POST (sin template)"""
    
    @transaction.atomic
    def post(self, request):
        try:
            from apps.sales_management.models import Cliente, Venta
            
            # Obtener datos del formulario
            cliente_id = request.POST.get('cliente')
            venta_id = request.POST.get('venta')
            monto_total = Decimal(request.POST.get('monto_total', '0'))
            fecha_vencimiento_str = request.POST.get('fecha_vencimiento')  # String
            descripcion = request.POST.get('descripcion', '')
            observaciones = request.POST.get('observaciones', '')
            
            # ✅ CONVERTIR STRING A DATE
            try:
                fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, "Fecha de vencimiento inválida")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Validar que la fecha de vencimiento sea futura
            if fecha_vencimiento <= timezone.now().date():
                messages.error(request, "La fecha de vencimiento debe ser posterior a hoy")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Validar cliente
            try:
                cliente = Cliente.objects.get(id=cliente_id, activo=True)
            except Cliente.DoesNotExist:
                messages.error(request, "Cliente no válido o inactivo")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Validar venta (opcional)
            venta = None
            if venta_id:
                try:
                    venta = Venta.objects.get(id=venta_id, cliente=cliente)
                except Venta.DoesNotExist:
                    messages.error(request, "Venta no válida")
                    return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Validar monto
            if monto_total <= 0:
                messages.error(request, "El monto debe ser mayor a cero")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Validar crédito disponible
            if monto_total > cliente.credito_disponible:
                messages.error(
                    request,
                    f"El monto (${monto_total}) excede el crédito disponible del cliente (${cliente.credito_disponible})"
                )
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Crear la cuenta por cobrar
            cuenta = CuentaPorCobrar.objects.create(
                cliente=cliente,
                venta=venta,
                monto_total=monto_total,
                fecha_emision=timezone.now().date(),
                fecha_vencimiento=fecha_vencimiento,  # ✅ Ahora es objeto date
                descripcion=descripcion,
                observaciones=observaciones,
                usuario_registro=request.user,
                estado='PENDIENTE',
                saldo_pendiente=monto_total
            )
            
            # Actualizar crédito disponible del cliente
            cliente.credito_disponible -= monto_total
            cliente.save()
            
            messages.success(
                request,
                f"✅ Cuenta por cobrar {cuenta.numero_cuenta} creada exitosamente"
            )
            
            return redirect('financial_management:cuenta_por_cobrar_list')
        
        except ValueError as e:
            messages.error(request, f"Error en los datos: {str(e)}")
            return redirect('financial_management:cuenta_por_cobrar_list')
        
        except Exception as e:
            messages.error(request, f"Error al crear la cuenta: {str(e)}")
            return redirect('financial_management:cuenta_por_cobrar_list')


class RegistrarPagoCuentaPorCobrarView(CreditoAccessMixin, View):
    """Registrar un pago de cliente (solo POST, sin template)"""
    
    @transaction.atomic
    def post(self, request, pk):
        try:
            cuenta = get_object_or_404(CuentaPorCobrar, pk=pk)
            
            # Verificar que la cuenta tenga saldo pendiente
            if cuenta.saldo_pendiente <= 0:
                messages.warning(request, "Esta cuenta ya está pagada completamente.")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Obtener datos del formulario
            monto = Decimal(request.POST.get('monto', '0'))
            metodo_pago = request.POST.get('metodo_pago', 'EFECTIVO')
            numero_comprobante = request.POST.get('numero_comprobante', '')
            banco = request.POST.get('banco', '')
            numero_cuenta_banco = request.POST.get('numero_cuenta_banco', '')
            observaciones = request.POST.get('observaciones', '')
            
            # Validar monto
            if monto <= 0:
                messages.error(request, "El monto debe ser mayor a cero")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            if monto > cuenta.saldo_pendiente:
                messages.error(
                    request,
                    f"El monto (${monto}) excede el saldo pendiente (${cuenta.saldo_pendiente})"
                )
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Registrar el pago usando el método del modelo
            pago = cuenta.registrar_pago(
                monto=monto,
                metodo_pago=metodo_pago,
                usuario=request.user,
                observaciones=observaciones,
                numero_comprobante=numero_comprobante
            )
            
            # Actualizar datos adicionales del pago
            pago.banco = banco
            pago.numero_cuenta_banco = numero_cuenta_banco
            pago.save()
            
            # Mensaje según el estado final
            if cuenta.estado == 'PAGADA':
                messages.success(
                    request,
                    f"✅ Pago de ${monto} registrado. ¡Cuenta {cuenta.numero_cuenta} pagada completamente!"
                )
            else:
                messages.success(
                    request,
                    f"✅ Pago de ${monto} registrado en cuenta {cuenta.numero_cuenta}. Saldo pendiente: ${cuenta.saldo_pendiente}"
                )
            
            return redirect('financial_management:cuenta_por_cobrar_list')
        
        except ValueError as e:
            messages.error(request, f"Error en los datos: {str(e)}")
            return redirect('financial_management:cuenta_por_cobrar_list')
        
        except Exception as e:
            messages.error(request, f"Error al registrar el pago: {str(e)}")
            return redirect('financial_management:cuenta_por_cobrar_list')


class CancelarCuentaPorCobrarView(SupervisorAccessMixin, View):
    """Cancelar una cuenta por cobrar (solo POST, sin template)"""
    
    @transaction.atomic
    def post(self, request, pk):
        try:
            cuenta = get_object_or_404(CuentaPorCobrar, pk=pk)
            
            # Verificar que se pueda cancelar
            if not cuenta.puede_cancelarse():
                messages.error(
                    request,
                    "No se puede cancelar una cuenta que ya tiene pagos registrados."
                )
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Obtener motivo de cancelación
            motivo = request.POST.get('motivo', '')
            
            if not motivo:
                messages.error(request, "Debe especificar el motivo de cancelación")
                return redirect('financial_management:cuenta_por_cobrar_list')
            
            # Cambiar estado a CANCELADA
            cuenta.estado = 'CANCELADA'
            cuenta.observaciones += f"\n\n[CANCELADA por {request.user.username}] {motivo}"
            cuenta.save()
            
            # Restaurar crédito del cliente
            cuenta.cliente.credito_disponible += cuenta.saldo_pendiente
            cuenta.cliente.save()
            
            messages.success(
                request,
                f"✅ Cuenta {cuenta.numero_cuenta} cancelada exitosamente."
            )
            
            return redirect('financial_management:cuenta_por_cobrar_list')
        
        except Exception as e:
            messages.error(request, f"Error al cancelar la cuenta: {str(e)}")
            return redirect('financial_management:cuenta_por_cobrar_list')


class ReporteAntiguedadSaldosCobrarView(CreditoAccessMixin, TemplateView):
    """Reporte de antigüedad de saldos por cobrar"""
    template_name = 'custom_admin/finanzas/reporte_antiguedad_cobrar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import ReporteCuentasPorCobrar
        
        # ✅ Resumen general
        resumen = ReporteCuentasPorCobrar.resumen_general()
        context['resumen'] = resumen
        
        # ✅ DEBUG: Imprimir para verificar
        print("=" * 50)
        print("RESUMEN GENERAL CUENTAS POR COBRAR:")
        print(f"Total por cobrar: {resumen.get('total_por_cobrar', 0)}")
        print(f"Total vencido: {resumen.get('total_vencido', 0)}")
        print(f"Total por vencer: {resumen.get('total_por_vencer', 0)}")
        print(f"Cuentas pendientes: {resumen.get('cuentas_pendientes', 0)}")
        print(f"Cuentas cobradas: {resumen.get('cuentas_cobradas', 0)}")
        print("=" * 50)
        
        # ✅ Antigüedad de saldos
        antiguedad = ReporteCuentasPorCobrar.antiguedad_saldos()
        context['antiguedad'] = antiguedad
        
        # ✅ DEBUG: Imprimir antigüedad
        print("ANTIGÜEDAD DE SALDOS:")
        for rango in antiguedad:
            print(f"  {rango}")
        print("=" * 50)
        
        # ✅ Clientes con cuentas vencidas
        clientes_vencidos = CuentaPorCobrar.objects.filter(
            estado='VENCIDA'
        ).values(
            'cliente__id',
            'cliente__nombres',
            'cliente__apellidos'
        ).annotate(
            total_vencido=Sum('saldo_pendiente'),
            cantidad_cuentas=Count('id'),
            dias_promedio=Avg('dias_vencidos')
        ).order_by('-total_vencido')[:10]
        
        context['clientes_vencidos'] = clientes_vencidos
        
        # ✅ DEBUG: Imprimir clientes vencidos
        print("CLIENTES VENCIDOS:")
        for cliente in clientes_vencidos:
            print(f"  {cliente}")
        print("=" * 50)
        
        # ✅ Top 10 cuentas vencidas
        top_vencidas = CuentaPorCobrar.objects.filter(
            estado='VENCIDA'
        ).select_related('cliente').order_by('-saldo_pendiente')[:10]
        
        context['top_vencidas'] = top_vencidas
        
        # ✅ DEBUG: Imprimir top vencidas
        print("TOP CUENTAS VENCIDAS:")
        for cuenta in top_vencidas:
            print(f"  {cuenta.numero_cuenta}: ${cuenta.saldo_pendiente}")
        print("=" * 50)
        
        return context


# ============================================================================
# CUENTAS POR PAGAR (DEUDAS CON PROVEEDORES)
# ============================================================================

class CuentaPorPagarListView(CreditoAccessMixin, ListView):
    """Lista de cuentas por pagar (deudas con proveedores)"""
    model = CuentaPorPagar
    template_name = 'custom_admin/finanzas/cuenta_por_pagar_list.html'
    context_object_name = 'cuentas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CuentaPorPagar.objects.select_related(
            'proveedor', 'usuario_registro'
        ).order_by('-fecha_emision')
        
        # Aplicar filtros del formulario
        form = BuscarCuentasPorPagarForm(self.request.GET)
        
        if form.is_valid():
            proveedor = form.cleaned_data.get('proveedor')
            if proveedor:
                queryset = queryset.filter(
                    Q(proveedor__nombre_comercial__icontains=proveedor) |
                    Q(proveedor__razon_social__icontains=proveedor) |
                    Q(proveedor__ruc_nit__icontains=proveedor)  # ✅ CORRECCIÓN
                )
            
            estado = form.cleaned_data.get('estado')
            if estado:
                queryset = queryset.filter(estado=estado)
            
            tipo_compra = form.cleaned_data.get('tipo_compra')
            if tipo_compra:
                queryset = queryset.filter(tipo_compra=tipo_compra)
            
            fecha_desde = form.cleaned_data.get('fecha_desde')
            if fecha_desde:
                queryset = queryset.filter(fecha_emision__gte=fecha_desde)
            
            fecha_hasta = form.cleaned_data.get('fecha_hasta')
            if fecha_hasta:
                queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
            
            solo_vencidas = form.cleaned_data.get('solo_vencidas')
            if solo_vencidas:
                queryset = queryset.filter(estado='VENCIDA')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Formulario de búsqueda
        context['buscar_form'] = BuscarCuentasPorPagarForm(self.request.GET)
        
        # Estadísticas generales
        from .models import ReporteCuentasPorPagar
        context['resumen'] = ReporteCuentasPorPagar.resumen_general()
        
        # Totales filtrados
        cuentas_filtradas = self.get_queryset()
        context['total_filtrado'] = cuentas_filtradas.aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        context['cantidad_filtrada'] = cuentas_filtradas.count()
        
        return context


class CuentaPorPagarDetailView(CreditoAccessMixin, DetailView):
    """Detalle de una cuenta por pagar con historial de pagos"""
    model = CuentaPorPagar
    template_name = 'custom_admin/financial/cuenta_por_pagar_detail.html'
    context_object_name = 'cuenta'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cuenta = self.get_object()
        
        # Historial de pagos
        context['pagos'] = cuenta.pagos.all().select_related('usuario').order_by('-fecha_pago')
        
        # Estadísticas de la cuenta
        context['total_pagado'] = cuenta.pagos.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')
        
        context['cantidad_pagos'] = cuenta.pagos.count()
        
        # Estado de vencimiento
        context['esta_vencida'] = cuenta.esta_vencida()
        context['dias_restantes'] = cuenta.dias_para_vencer()
        
        return context


class CuentaPorPagarCreateView(CreditoAccessMixin, View):
    """Crear nueva cuenta por pagar vía POST (sin template)"""
    
    @transaction.atomic
    def post(self, request):
        try:
            from apps.inventory_management.models import Proveedor
            
            # Obtener datos del formulario
            proveedor_id = request.POST.get('proveedor')
            numero_factura = request.POST.get('numero_factura_proveedor', '')
            tipo_compra = request.POST.get('tipo_compra', 'NORMAL')
            monto_total = Decimal(request.POST.get('monto_total', '0'))
            fecha_factura_str = request.POST.get('fecha_factura')
            fecha_vencimiento_str = request.POST.get('fecha_vencimiento')
            descripcion = request.POST.get('descripcion', '')
            observaciones = request.POST.get('observaciones', '')
            
            # ✅ CONVERTIR STRINGS A DATE
            try:
                fecha_factura = datetime.strptime(fecha_factura_str, '%Y-%m-%d').date()
                fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, "Fechas inválidas")
                return redirect('financial_management:cuenta_por_pagar_list')
            
            # Validar que fecha de vencimiento sea posterior a fecha de factura
            if fecha_vencimiento < fecha_factura:
                messages.error(request, "La fecha de vencimiento debe ser posterior a la fecha de factura")
                return redirect('financial_management:cuenta_por_pagar_list')
            
            # Validar proveedor
            try:
                proveedor = Proveedor.objects.get(id=proveedor_id, activo=True)
            except Proveedor.DoesNotExist:
                messages.error(request, "Proveedor no válido o inactivo")
                return redirect('financial_management:cuenta_por_pagar_list')
            
            # Validar monto
            if monto_total <= 0:
                messages.error(request, "El monto debe ser mayor a cero")
                return redirect('financial_management:cuenta_por_pagar_list')
            
            # Crear la cuenta por pagar
            cuenta = CuentaPorPagar.objects.create(
                proveedor=proveedor,
                numero_factura_proveedor=numero_factura,
                tipo_compra=tipo_compra,
                monto_total=monto_total,
                fecha_emision=timezone.now().date(),
                fecha_factura=fecha_factura,  # ✅ Ahora es objeto date
                fecha_vencimiento=fecha_vencimiento,  # ✅ Ahora es objeto date
                descripcion=descripcion,
                observaciones=observaciones,
                usuario_registro=request.user,
                estado='PENDIENTE',
                saldo_pendiente=monto_total
            )
            
            messages.success(
                request,
                f"✅ Cuenta por pagar {cuenta.numero_cuenta} creada exitosamente"
            )
            
            return redirect('financial_management:cuenta_por_pagar_list')
        
        except ValueError as e:
            messages.error(request, f"Error en los datos: {str(e)}")
            return redirect('financial_management:cuenta_por_pagar_list')
        
        except Exception as e:
            messages.error(request, f"Error al crear la cuenta: {str(e)}")
            return redirect('financial_management:cuenta_por_pagar_list')


class RegistrarPagoCuentaPorPagarView(CreditoAccessMixin, View):
    """Registrar un pago a proveedor (solo POST, sin template)"""
    
    @transaction.atomic
    def post(self, request, pk):
        try:
            cuenta = get_object_or_404(CuentaPorPagar, pk=pk)
            
            # Verificar que la cuenta tenga saldo pendiente
            if cuenta.saldo_pendiente <= 0:
                messages.warning(request, "Esta cuenta ya está pagada completamente.")
                return redirect('financial_management:cuenta_por_pagar_list')
            
            # Obtener datos del formulario
            monto = Decimal(request.POST.get('monto', '0'))
            metodo_pago = request.POST.get('metodo_pago', 'EFECTIVO')
            numero_comprobante = request.POST.get('numero_comprobante', '')
            banco = request.POST.get('banco', '')
            numero_cuenta_banco = request.POST.get('numero_cuenta_banco', '')
            observaciones = request.POST.get('observaciones', '')
            
            # Validar monto
            if monto <= 0:
                messages.error(request, "El monto debe ser mayor a cero")
                return redirect('financial_management:cuenta_por_pagar_list')
            
            if monto > cuenta.saldo_pendiente:
                messages.error(
                    request,
                    f"El monto (${monto}) excede el saldo pendiente (${cuenta.saldo_pendiente})"
                )
                return redirect('financial_management:cuenta_por_pagar_list')
            
            # Registrar el pago usando el método del modelo
            pago = cuenta.registrar_pago(
                monto=monto,
                metodo_pago=metodo_pago,
                usuario=request.user,
                observaciones=observaciones,
                numero_comprobante=numero_comprobante
            )
            
            # Actualizar datos adicionales del pago
            pago.banco = banco
            pago.numero_cuenta_banco = numero_cuenta_banco
            pago.save()
            
            # Mensaje según el estado final
            if cuenta.estado == 'PAGADA':
                messages.success(
                    request,
                    f"✅ Pago de ${monto} registrado. ¡Cuenta {cuenta.numero_cuenta} pagada completamente!"
                )
            else:
                messages.success(
                    request,
                    f"✅ Pago de ${monto} registrado en cuenta {cuenta.numero_cuenta}. Saldo pendiente: ${cuenta.saldo_pendiente}"
                )
            
            return redirect('financial_management:cuenta_por_pagar_list')
        
        except ValueError as e:
            messages.error(request, f"Error en los datos: {str(e)}")
            return redirect('financial_management:cuenta_por_pagar_list')
        
        except Exception as e:
            messages.error(request, f"Error al registrar el pago: {str(e)}")
            return redirect('financial_management:cuenta_por_pagar_list')


class ReporteAntiguedadSaldosPagarView(CreditoAccessMixin, TemplateView):
    """Reporte de antigüedad de saldos por pagar"""
    template_name = 'custom_admin/finanzas/reporte_antiguedad_pagar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ✅ Resumen general
        resumen = ReporteCuentasPorPagar.resumen_general()
        context['resumen'] = resumen
        
        # ✅ DEBUG: Imprimir para verificar
        print("=" * 50)
        print("RESUMEN GENERAL:")
        print(f"Total por pagar: {resumen.get('total_por_pagar', 0)}")
        print(f"Total vencido: {resumen.get('total_vencido', 0)}")
        print(f"Total por vencer: {resumen.get('total_por_vencer', 0)}")
        print(f"Cuentas pendientes: {resumen.get('cuentas_pendientes', 0)}")
        print(f"Cuentas pagadas: {resumen.get('cuentas_pagadas', 0)}")
        print("=" * 50)
        
        # ✅ Antigüedad de saldos
        antiguedad = ReporteCuentasPorPagar.antiguedad_saldos()
        context['antiguedad'] = antiguedad
        
        # ✅ DEBUG: Imprimir antigüedad
        print("ANTIGÜEDAD DE SALDOS:")
        for rango in antiguedad:
            print(f"  {rango}")
        print("=" * 50)
        
        # ✅ Proveedores con deudas vencidas
        proveedores_vencidos = CuentaPorPagar.objects.filter(
            estado='VENCIDA'
        ).values(
            'proveedor__id',
            'proveedor__nombre_comercial'
        ).annotate(
            total_vencido=Sum('saldo_pendiente'),
            cantidad_cuentas=Count('id'),
            dias_promedio=Avg('dias_vencidos')
        ).order_by('-total_vencido')[:10]
        
        context['proveedores_vencidos'] = proveedores_vencidos
        
        # ✅ DEBUG: Imprimir proveedores vencidos
        print("PROVEEDORES VENCIDOS:")
        for prov in proveedores_vencidos:
            print(f"  {prov}")
        print("=" * 50)
        
        # ✅ Top 10 cuentas vencidas
        top_vencidas = CuentaPorPagar.objects.filter(
            estado='VENCIDA'
        ).select_related('proveedor').order_by('-saldo_pendiente')[:10]
        
        context['top_vencidas'] = top_vencidas
        
        # ✅ DEBUG: Imprimir top vencidas
        print("TOP CUENTAS VENCIDAS:")
        for cuenta in top_vencidas:
            print(f"  {cuenta.numero_cuenta}: ${cuenta.saldo_pendiente}")
        print("=" * 50)
        
        return context


# ============================================================================
# APIS Y UTILIDADES PARA CRÉDITOS
# ============================================================================

class EstadoCreditoClienteAPIView(CreditoAccessMixin, View):
    """API para obtener el estado del crédito de un cliente"""
    
    def get(self, request, cliente_id):
        from apps.sales_management.models import Cliente
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        
        # Cuentas pendientes
        cuentas_pendientes = CuentaPorCobrar.objects.filter(
            cliente=cliente,
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        )
        
        data = {
            'cliente': {
                'id': str(cliente.id),
                'nombre': cliente.nombre_completo(),
                'nit': cliente.nit
            },
            'credito': {
                'limite': float(cliente.limite_credito),
                'disponible': float(cliente.credito_disponible),
                'usado': float(cliente.limite_credito - cliente.credito_disponible),
                'porcentaje_usado': float(
                    (cliente.limite_credito - cliente.credito_disponible) / 
                    cliente.limite_credito * 100
                ) if cliente.limite_credito > 0 else 0
            },
            'cuentas_pendientes': {
                'total': cuentas_pendientes.aggregate(
                    total=Sum('saldo_pendiente')
                )['total'] or 0,
                'cantidad': cuentas_pendientes.count(),
                'vencidas': cuentas_pendientes.filter(estado='VENCIDA').count()
            }
        }
        
        return JsonResponse(data)
    from apps.sales_management.models import Cliente, Venta

from apps.sales_management.models import Cliente, Venta

class ClientesAPIView(View):
    """API para obtener lista de clientes"""
    
    def get(self, request):
        clientes = Cliente.objects.filter(activo=True).values(
            'id', 'nombres', 'apellidos', 'numero_documento'  # ✅ CORRECTO
        )
        
        data = [
            {
                'id': str(c['id']),
                'nombre': f"{c['nombres']} {c['apellidos']}",
                'nit': c['numero_documento']  # ✅ Usar numero_documento
            }
            for c in clientes
        ]
        
        return JsonResponse(data, safe=False)


class ClienteVentasAPIView(View):
    """API para obtener ventas de un cliente"""
    
    def get(self, request, cliente_id):
        ventas = Venta.objects.filter(
            cliente_id=cliente_id,
            estado='COMPLETADA'
        ).values(
            'id', 'numero_venta', 'total', 'fecha_venta'
        ).order_by('-fecha_venta')[:20]
        
        data = [
            {
                'id': str(v['id']),
                'numero_venta': v['numero_venta'],
                'total': float(v['total']),
                'fecha': v['fecha_venta'].strftime('%d/%m/%Y')
            }
            for v in ventas
        ]
        
        return JsonResponse(data, safe=False)


class EstadoCreditoClienteAPIView(CreditoAccessMixin, View):
    """API para obtener el estado del crédito de un cliente"""
    
    def get(self, request, cliente_id):
        from apps.sales_management.models import Cliente
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        
        # Cuentas pendientes
        cuentas_pendientes = CuentaPorCobrar.objects.filter(
            cliente=cliente,
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        )
        
        data = {
            'cliente': {
                'id': str(cliente.id),
                'nombre': cliente.nombre_completo(),
                'nit': cliente.numero_documento  # ✅ CORRECCIÓN: usar numero_documento
            },
            'credito': {
                'limite': float(cliente.limite_credito),
                'disponible': float(cliente.credito_disponible),
                'usado': float(cliente.limite_credito - cliente.credito_disponible),
                'porcentaje_usado': float(
                    (cliente.limite_credito - cliente.credito_disponible) / 
                    cliente.limite_credito * 100
                ) if cliente.limite_credito > 0 else 0
            },
            'cuentas_pendientes': {
                'total': cuentas_pendientes.aggregate(
                    total=Sum('saldo_pendiente')
                )['total'] or 0,
                'cantidad': cuentas_pendientes.count(),
                'vencidas': cuentas_pendientes.filter(estado='VENCIDA').count()
            }
        }
        
        return JsonResponse(data)


class CuentaPorCobrarDetalleAPIView(CreditoAccessMixin, View):
    """API para obtener detalle de cuenta por cobrar en JSON"""
    
    def get(self, request, cuenta_id):
        cuenta = get_object_or_404(CuentaPorCobrar, pk=cuenta_id)
        
        # Obtener pagos
        pagos = cuenta.pagos.all().select_related('usuario').order_by('-fecha_pago')
        pagos_data = [
            {
                'id': str(p.id),
                'fecha': p.fecha_pago.strftime('%d/%m/%Y %H:%M'),
                'monto': float(p.monto),
                'metodo_pago': p.get_metodo_pago_display(),
                'numero_comprobante': p.numero_comprobante or '-',
                'usuario': p.usuario.get_full_name() if p.usuario else 'N/A',
                'observaciones': p.observaciones or ''
            }
            for p in pagos
        ]
        
        # ✅ CALCULAR porcentaje_pagado aquí
        porcentaje_pagado = (cuenta.monto_pagado / cuenta.monto_total * 100) if cuenta.monto_total > 0 else 0
        
        data = {
            'id': str(cuenta.id),
            'numero_cuenta': cuenta.numero_cuenta,
            'cliente': {
                'nombre': cuenta.cliente.nombre_completo(),
                'nit': cuenta.cliente.numero_documento,  # ✅ CORRECCIÓN
                'limite_credito': float(cuenta.cliente.limite_credito),
                'credito_disponible': float(cuenta.cliente.credito_disponible),
                'credito_usado': float(cuenta.cliente.limite_credito - cuenta.cliente.credito_disponible),
            },
            'venta': {
                'numero': cuenta.venta.numero_venta if cuenta.venta else None,
                'id': str(cuenta.venta.id) if cuenta.venta else None
            } if cuenta.venta else None,
            'monto_total': float(cuenta.monto_total),
            'monto_pagado': float(cuenta.monto_pagado),
            'saldo_pendiente': float(cuenta.saldo_pendiente),
            'porcentaje_pagado': float(porcentaje_pagado),  # ✅ CORRECCIÓN
            'estado': cuenta.estado,
            'estado_display': cuenta.get_estado_display(),
            'fecha_emision': cuenta.fecha_emision.strftime('%d/%m/%Y'),
            'fecha_vencimiento': cuenta.fecha_vencimiento.strftime('%d/%m/%Y'),
            'dias_para_vencer': cuenta.dias_para_vencer(),
            'dias_vencidos': cuenta.dias_vencidos,
            'esta_vencida': cuenta.esta_vencida(),
            'descripcion': cuenta.descripcion or '',
            'observaciones': cuenta.observaciones or '',
            'pagos': pagos_data,
            'puede_cancelarse': cuenta.puede_cancelarse(),
        }
        
        return JsonResponse(data)

class ProveedoresAPIView(View):
    """API para obtener lista de proveedores"""
    
    def get(self, request):
        proveedores = Proveedor.objects.filter(activo=True).values(
            'id', 'nombre_comercial', 'razon_social', 'ruc_nit'  # ✅
        )
        
        data = [
            {
                'id': str(p['id']),
                'nombre': p['nombre_comercial'] or p['razon_social'],
                'nit': p['ruc_nit'] or 'N/A'  # ✅
            }
            for p in proveedores
        ]
        
        return JsonResponse(data, safe=False)


class EstadoCreditoProveedorAPIView(CreditoAccessMixin, View):
    """API para obtener el estado de deuda con un proveedor"""
    
    def get(self, request, proveedor_id):
        from apps.inventory_management.models import Proveedor
        proveedor = get_object_or_404(Proveedor, pk=proveedor_id)
        
        # Cuentas pendientes
        cuentas_pendientes = CuentaPorPagar.objects.filter(
            proveedor=proveedor,
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        )
        
        data = {
            'proveedor': {
                'id': str(proveedor.id),
                'nombre': proveedor.nombre_comercial or proveedor.razon_social,
                'nit': proveedor.ruc_nit or 'N/A'
            },
            'cuentas_pendientes': {
                'total': float(cuentas_pendientes.aggregate(
                    total=Sum('saldo_pendiente')
                )['total'] or 0),
                'cantidad': cuentas_pendientes.count(),
                'vencidas': cuentas_pendientes.filter(estado='VENCIDA').count()
            }
        }
        
        return JsonResponse(data)


class CuentaPorPagarDetalleAPIView(CreditoAccessMixin, View):
    """API para obtener detalle de cuenta por pagar en JSON"""
    
    def get(self, request, cuenta_id):
        cuenta = get_object_or_404(CuentaPorPagar, pk=cuenta_id)
        
        # Obtener pagos
        pagos = cuenta.pagos.all().select_related('usuario').order_by('-fecha_pago')
        pagos_data = [
            {
                'id': str(p.id),
                'fecha': p.fecha_pago.strftime('%d/%m/%Y %H:%M'),
                'monto': float(p.monto),
                'metodo_pago': p.get_metodo_pago_display(),
                'numero_comprobante': p.numero_comprobante or '-',
                'usuario': p.usuario.get_full_name() if p.usuario else 'N/A',
                'observaciones': p.observaciones or ''
            }
            for p in pagos
        ]
        
        # Calcular porcentaje pagado
        porcentaje_pagado = (cuenta.monto_pagado / cuenta.monto_total * 100) if cuenta.monto_total > 0 else 0
        
        data = {
            'id': str(cuenta.id),
            'numero_cuenta': cuenta.numero_cuenta,
            'proveedor': {
                'nombre': cuenta.proveedor.nombre_comercial or cuenta.proveedor.razon_social,
                'nit': cuenta.proveedor.ruc_nit or 'N/A'
            },
            'tipo_compra': cuenta.tipo_compra,
            'tipo_compra_display': cuenta.get_tipo_compra_display(),
            'numero_factura_proveedor': cuenta.numero_factura_proveedor or '-',
            'monto_total': float(cuenta.monto_total),
            'monto_pagado': float(cuenta.monto_pagado),
            'saldo_pendiente': float(cuenta.saldo_pendiente),
            'porcentaje_pagado': float(porcentaje_pagado),
            'estado': cuenta.estado,
            'estado_display': cuenta.get_estado_display(),
            'fecha_emision': cuenta.fecha_emision.strftime('%d/%m/%Y'),
            'fecha_factura': cuenta.fecha_factura.strftime('%d/%m/%Y'),
            'fecha_vencimiento': cuenta.fecha_vencimiento.strftime('%d/%m/%Y'),
            'dias_para_vencer': cuenta.dias_para_vencer(),
            'dias_vencidos': cuenta.dias_vencidos,
            'esta_vencida': cuenta.esta_vencida(),
            'descripcion': cuenta.descripcion or '',
            'observaciones': cuenta.observaciones or '',
            'pagos': pagos_data
        }
        
        return JsonResponse(data)