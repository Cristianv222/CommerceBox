# apps/financial_management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta, datetime

from .models import (
    Caja, MovimientoCaja, ArqueoCaja,
    CajaChica, MovimientoCajaChica
)
from .forms import (
    CajaForm, AperturaCajaForm, CierreCajaForm, MovimientoCajaForm,
    CajaChicaForm, GastoCajaChicaForm, ReposicionCajaChicaForm,
    BuscarMovimientosForm
)
from .mixins import (
    FinancialAccessMixin, CajaEditMixin, CajeroAccessMixin,
    SupervisorAccessMixin, CajaChicaAccessMixin, FormMessagesMixin
)


# ============================================================================
# DASHBOARD FINANCIERO
# ============================================================================

class FinancialDashboardView(FinancialAccessMixin, TemplateView):
    """Dashboard principal del módulo financiero"""
    template_name = 'financial/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cajas abiertas
        cajas_abiertas = Caja.objects.filter(
            estado='ABIERTA',
            activa=True
        )
        context['cajas_abiertas'] = cajas_abiertas
        context['total_cajas_abiertas'] = cajas_abiertas.count()
        
        # Total en cajas abiertas
        context['total_efectivo_cajas'] = cajas_abiertas.aggregate(
            total=Sum('monto_actual')
        )['total'] or Decimal('0')
        
        # Ventas del día
        hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ventas_hoy = MovimientoCaja.objects.filter(
            tipo_movimiento='VENTA',
            fecha_movimiento__gte=hoy_inicio
        ).aggregate(
            total=Sum('monto'),
            cantidad=Count('id')
        )
        context['ventas_hoy'] = ventas_hoy['total'] or Decimal('0')
        context['cantidad_ventas_hoy'] = ventas_hoy['cantidad'] or 0
        
        # Cajas chicas
        cajas_chicas = CajaChica.objects.filter(estado='ACTIVA')
        context['cajas_chicas'] = cajas_chicas
        context['cajas_chicas_criticas'] = cajas_chicas.filter(
            monto_actual__lte=F('umbral_reposicion')
        ).count()
        
        # Últimos movimientos
        context['ultimos_movimientos'] = MovimientoCaja.objects.select_related(
            'caja', 'usuario'
        ).order_by('-fecha_movimiento')[:10]
        
        # Arqueos recientes
        context['arqueos_recientes'] = ArqueoCaja.objects.select_related(
            'caja', 'usuario_cierre'
        ).order_by('-fecha_cierre')[:5]
        
        # Estadísticas de la semana
        hace_7_dias = timezone.now() - timedelta(days=7)
        movimientos_semana = MovimientoCaja.objects.filter(
            fecha_movimiento__gte=hace_7_dias
        )
        
        context['ingresos_semana'] = movimientos_semana.filter(
            tipo_movimiento__in=['VENTA', 'INGRESO']
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        context['retiros_semana'] = movimientos_semana.filter(
            tipo_movimiento='RETIRO'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
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

class RegistrarMovimientoCajaView(CajeroAccessMixin, TemplateView):
    """Registrar movimiento manual en caja (ingreso/retiro)"""
    template_name = 'financial/movimiento_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja = get_object_or_404(Caja, pk=self.kwargs['pk'])
        
        if caja.estado != 'ABIERTA':
            messages.error(self.request, "No se pueden registrar movimientos en una caja cerrada.")
            return redirect('financial_management:caja_detail', pk=caja.pk)
        
        context['caja'] = caja
        context['form'] = MovimientoCajaForm(caja=caja, usuario=self.request.user)
        return context
    
    @transaction.atomic
    def post(self, request, pk):
        caja = get_object_or_404(Caja, pk=pk)
        form = MovimientoCajaForm(
            request.POST,
            caja=caja,
            usuario=request.user
        )
        
        if form.is_valid():
            tipo_movimiento = form.cleaned_data['tipo_movimiento']
            monto = form.cleaned_data['monto']
            observaciones = form.cleaned_data['observaciones']
            
            # Calcular saldos
            saldo_anterior = caja.monto_actual
            
            if tipo_movimiento in ['INGRESO', 'AJUSTE_POSITIVO']:
                caja.monto_actual += monto
                monto_movimiento = monto
            else:  # RETIRO, AJUSTE_NEGATIVO
                caja.monto_actual -= monto
                monto_movimiento = -monto
            
            caja.save()
            
            # Registrar movimiento
            MovimientoCaja.objects.create(
                caja=caja,
                tipo_movimiento=tipo_movimiento,
                monto=abs(monto_movimiento),
                saldo_anterior=saldo_anterior,
                saldo_nuevo=caja.monto_actual,
                usuario=request.user,
                observaciones=observaciones
            )
            
            messages.success(
                request,
                f"Movimiento registrado exitosamente. Nuevo saldo: ${caja.monto_actual}"
            )
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
        queryset = super().get_queryset().select_related('caja', 'usuario_cierre')
        
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
        context['cajas'] = Caja.objects.filter(activa=True)
        return context


class ArqueoDetailView(FinancialAccessMixin, DetailView):
    """Detalle de un arqueo"""
    model = ArqueoCaja
    template_name = 'financial/arqueo_detail.html'
    context_object_name = 'arqueo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arqueo = self.get_object()
        
        # Movimientos de la sesión
        context['movimientos'] = MovimientoCaja.objects.filter(
            caja=arqueo.caja,
            fecha_movimiento__gte=arqueo.fecha_apertura,
            fecha_movimiento__lte=arqueo.fecha_cierre
        ).select_related('usuario').order_by('fecha_movimiento')
        
        return context
class CajaChicaListView(CajaChicaAccessMixin, ListView):
    """Lista de cajas chicas"""
    model = CajaChica
    template_name = 'financial/caja_chica_list.html'
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
    """Reponer el fondo de caja chica"""
    template_name = 'financial/reposicion_caja_chica.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caja_chica = get_object_or_404(CajaChica, pk=self.kwargs['pk'])
        
        context['caja_chica'] = caja_chica
        context['form'] = ReposicionCajaChicaForm(caja_chica=caja_chica)
        
        # Gastos desde última reposición
        if caja_chica.fecha_ultima_reposicion:
            gastos = MovimientoCajaChica.objects.filter(
                caja_chica=caja_chica,
                tipo_movimiento='GASTO',
                fecha_movimiento__gte=caja_chica.fecha_ultima_reposicion
            )
        else:
            gastos = MovimientoCajaChica.objects.filter(
                caja_chica=caja_chica,
                tipo_movimiento='GASTO'
            )
        
        context['gastos_periodo'] = gastos.order_by('-fecha_movimiento')
        context['total_gastado'] = gastos.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')
        
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
