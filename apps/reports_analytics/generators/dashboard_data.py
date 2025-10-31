# apps/reports_analytics/generators/dashboard_data.py

"""
Generador de datos para Dashboard en tiempo real
Métricas principales del negocio
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from datetime import timedelta, datetime

from apps.inventory_management.models import (
    Producto, Quintal, ProductoNormal, Categoria
)
from apps.sales_management.models import Venta, DetalleVenta, Cliente
from apps.financial_management.models import Caja, MovimientoCaja, CajaChica
from apps.stock_alert_system.models import AlertaStock


class DashboardDataGenerator:
    """
    Genera datos para el dashboard principal
    """
    
    def __init__(self, fecha=None):
        """
        Args:
            fecha: Fecha para generar el dashboard (por defecto hoy)
        """
        self.fecha = fecha or timezone.now().date()
        self.inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    def generar_dashboard_completo(self):
        """
        Genera todas las métricas del dashboard
        
        Returns:
            dict: Dashboard completo con todas las secciones
        """
        return {
            'resumen_ejecutivo': self.get_resumen_ejecutivo(),
            'ventas': self.get_metricas_ventas(),
            'inventario': self.get_metricas_inventario(),
            'financiero': self.get_metricas_financiero(),
            'alertas': self.get_alertas_criticas(),
            'top_productos': self.get_productos_mas_vendidos(limite=10),
            'ventas_por_categoria': self.get_ventas_por_categoria(),
            'tendencias': self.get_tendencias_semanales(),
            'comparativas': self.get_comparativas(),
        }
    
    def get_resumen_ejecutivo(self):
        """
        Resumen ejecutivo con KPIs principales
        """
        # Ventas del día
        ventas_dia = Venta.objects.filter(
            fecha_venta__gte=self.inicio_dia,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id')
        )
        
        # Ventas del mes
        ventas_mes = Venta.objects.filter(
            fecha_venta__gte=self.inicio_mes,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id')
        )
        
        # Ticket promedio
        ticket_promedio_dia = (
            ventas_dia['total'] / ventas_dia['cantidad'] 
            if ventas_dia['cantidad'] > 0 else Decimal('0')
        )
        
        # Valor del inventario
        from apps.inventory_management.services.stock_service import StockService
        valor_inventario = StockService.calcular_valor_inventario()
        
        # Caja actual
        caja_abierta = Caja.objects.filter(estado='ABIERTA').first()
        efectivo_caja = caja_abierta.monto_actual if caja_abierta else Decimal('0')
        
        return {
            'ventas_dia': {
                'total': ventas_dia['total'],
                'cantidad': ventas_dia['cantidad'],
                'ticket_promedio': ticket_promedio_dia.quantize(Decimal('0.01'))
            },
            'ventas_mes': {
                'total': ventas_mes['total'],
                'cantidad': ventas_mes['cantidad']
            },
            'inventario': {
                'valor_total': valor_inventario['valor_total'],
                'valor_quintales': valor_inventario['valor_quintales'],
                'valor_productos_normales': valor_inventario['valor_productos_normales']
            },
            'caja': {
                'efectivo_disponible': efectivo_caja,
                'estado_caja': 'ABIERTA' if caja_abierta else 'CERRADA'
            }
        }
    
    def get_metricas_ventas(self):
        """
        Métricas detalladas de ventas
        """
        # Ventas del día
        ventas_dia = DetalleVenta.objects.filter(
            venta__fecha_venta__gte=self.inicio_dia,
            venta__estado='COMPLETADA'
        )
        
        # Calcular utilidad del día
        utilidad_dia = ventas_dia.aggregate(
            ventas=Coalesce(Sum('total'), Decimal('0')),
            costos=Coalesce(Sum('costo_total'), Decimal('0'))
        )
        utilidad_dia['utilidad'] = utilidad_dia['ventas'] - utilidad_dia['costos']
        utilidad_dia['margen'] = (
            (utilidad_dia['utilidad'] / utilidad_dia['ventas'] * 100)
            if utilidad_dia['ventas'] > 0 else Decimal('0')
        )
        
        # Ventas por tipo de producto
        ventas_quintales = ventas_dia.filter(
            producto__tipo_inventario='QUINTAL'
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))
        
        ventas_normales = ventas_dia.filter(
            producto__tipo_inventario='NORMAL'
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))
        
        # Ventas por forma de pago
        from apps.sales_management.models import Pago
        pagos_dia = Pago.objects.filter(
            venta__fecha_venta__gte=self.inicio_dia,
            venta__estado='COMPLETADA'
        ).values('forma_pago').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        )
        
        # Comparativa con ayer
        ayer = self.inicio_dia - timedelta(days=1)
        ventas_ayer = Venta.objects.filter(
            fecha_venta__gte=ayer,
            fecha_venta__lt=self.inicio_dia,
            estado='COMPLETADA'
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))
        
        variacion_dia = (
            ((utilidad_dia['ventas'] - ventas_ayer['total']) / ventas_ayer['total'] * 100)
            if ventas_ayer['total'] > 0 else Decimal('0')
        )
        
        return {
            'dia': {
                'ventas_totales': utilidad_dia['ventas'],
                'costos_totales': utilidad_dia['costos'],
                'utilidad_bruta': utilidad_dia['utilidad'],
                'margen_porcentaje': utilidad_dia['margen'].quantize(Decimal('0.01'))
            },
            'por_tipo': {
                'quintales': ventas_quintales['total'],
                'productos_normales': ventas_normales['total']
            },
            'formas_pago': list(pagos_dia),
            'comparativa': {
                'ventas_ayer': ventas_ayer['total'],
                'variacion_porcentaje': variacion_dia.quantize(Decimal('0.01'))
            }
        }
    
    def get_metricas_inventario(self):
        """
        Métricas de inventario
        """
        # Quintales
        quintales_stats = Quintal.objects.filter(estado='DISPONIBLE').aggregate(
            total=Count('id'),
            peso_total=Coalesce(Sum('peso_actual'), Decimal('0')),
            valor_total=Coalesce(Sum(F('peso_actual') * F('costo_por_unidad')), Decimal('0'))
        )
        
        quintales_criticos = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__lte=F('peso_inicial') * 0.1
        ).count()
        
        # Productos Normales
        productos_stats = ProductoNormal.objects.aggregate(
            total=Count('id'),
            con_stock=Count('id', filter=Q(stock_actual__gt=0)),
            valor_total=Coalesce(Sum(F('stock_actual') * F('costo_unitario')), Decimal('0'))
        )
        
        productos_criticos = ProductoNormal.objects.filter(
            stock_actual__lte=F('stock_minimo'),
            stock_actual__gt=0
        ).count()
        
        productos_agotados = ProductoNormal.objects.filter(
            stock_actual=0
        ).count()
        
        # Alertas de stock
        alertas_activas = AlertaStock.objects.filter(
            resuelta=False
        ).count()
        
        # Productos próximos a vencer
        proximos_vencer = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=self.fecha + timedelta(days=7),
            fecha_vencimiento__gte=self.fecha
        ).count()
        
        return {
            'quintales': {
                'total_disponibles': quintales_stats['total'],
                'peso_total': quintales_stats['peso_total'],
                'valor_total': quintales_stats['valor_total'],
                'criticos': quintales_criticos,
                'proximos_vencer': proximos_vencer
            },
            'productos_normales': {
                'total': productos_stats['total'],
                'con_stock': productos_stats['con_stock'],
                'valor_total': productos_stats['valor_total'],
                'criticos': productos_criticos,
                'agotados': productos_agotados
            },
            'alertas': {
                'total_activas': alertas_activas,
                'requieren_atencion': quintales_criticos + productos_criticos + productos_agotados
            }
        }
    
    def get_metricas_financiero(self):
        """
        Métricas financieras
        """
        # Caja principal
        caja_abierta = Caja.objects.filter(estado='ABIERTA').first()
        
        if caja_abierta:
            movimientos_dia = MovimientoCaja.objects.filter(
                caja=caja_abierta,
                fecha_movimiento__gte=self.inicio_dia
            )
            
            ingresos = movimientos_dia.filter(
                tipo_movimiento__in=['VENTA', 'INGRESO', 'AJUSTE_POSITIVO']
            ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))
            
            egresos = movimientos_dia.filter(
                tipo_movimiento__in=['RETIRO', 'AJUSTE_NEGATIVO']
            ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))
            
            caja_data = {
                'estado': 'ABIERTA',
                'monto_apertura': caja_abierta.monto_apertura,
                'monto_actual': caja_abierta.monto_actual,
                'ingresos_dia': ingresos['total'],
                'egresos_dia': egresos['total'],
                'movimientos_dia': movimientos_dia.count()
            }
        else:
            caja_data = {
                'estado': 'CERRADA',
                'mensaje': 'No hay caja abierta'
            }
        
        # Caja Chica
        caja_chica = CajaChica.objects.filter(estado='ACTIVA').first()
        if caja_chica:
            necesita_reposicion = caja_chica.necesita_reposicion()
            caja_chica_data = {
                'monto_actual': caja_chica.monto_actual,
                'monto_fondo': caja_chica.monto_fondo,
                'necesita_reposicion': necesita_reposicion,
                'monto_a_reponer': caja_chica.monto_a_reponer() if necesita_reposicion else Decimal('0')
            }
        else:
            caja_chica_data = None
        
        # Créditos pendientes
        from apps.sales_management.models import Venta
        creditos_pendientes = Venta.objects.filter(
            tipo_venta='CREDITO',
            estado='COMPLETADA'
        ).annotate(
            saldo=F('total') - F('monto_pagado')
        ).filter(saldo__gt=0).aggregate(
            total=Coalesce(Sum('saldo'), Decimal('0')),
            cantidad=Count('id')
        )
        
        return {
            'caja_principal': caja_data,
            'caja_chica': caja_chica_data,
            'creditos_pendientes': creditos_pendientes
        }
    
    def get_alertas_criticas(self):
        """
        Alertas que requieren atención inmediata
        """
        alertas = []
        
        # Productos agotados
        agotados = ProductoNormal.objects.filter(
            stock_actual=0,
            producto__activo=True
        ).select_related('producto').count()
        
        if agotados > 0:
            alertas.append({
                'tipo': 'PRODUCTOS_AGOTADOS',
                'nivel': 'CRITICO',
                'mensaje': f'{agotados} producto(s) agotado(s)',
                'cantidad': agotados
            })
        
        # Productos críticos
        criticos = ProductoNormal.objects.filter(
            stock_actual__lte=F('stock_minimo'),
            stock_actual__gt=0
        ).count()
        
        if criticos > 0:
            alertas.append({
                'tipo': 'STOCK_CRITICO',
                'nivel': 'ALTO',
                'mensaje': f'{criticos} producto(s) con stock crítico',
                'cantidad': criticos
            })
        
        # Quintales próximos a vencer
        proximos_vencer = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=self.fecha + timedelta(days=3),
            fecha_vencimiento__gte=self.fecha
        ).count()
        
        if proximos_vencer > 0:
            alertas.append({
                'tipo': 'PROXIMOS_VENCER',
                'nivel': 'ALTO',
                'mensaje': f'{proximos_vencer} quintal(es) vencen en 3 días o menos',
                'cantidad': proximos_vencer
            })
        
        # Caja chica baja
        caja_chica = CajaChica.objects.filter(estado='ACTIVA').first()
        if caja_chica and caja_chica.necesita_reposicion():
            alertas.append({
                'tipo': 'CAJA_CHICA_BAJA',
                'nivel': 'MEDIO',
                'mensaje': f'Caja chica necesita reposición: ${caja_chica.monto_a_reponer()}',
                'monto': caja_chica.monto_a_reponer()
            })
        
        return alertas
    
    def get_productos_mas_vendidos(self, limite=10):
        """
        Top productos más vendidos del día
        """
        productos_dia = DetalleVenta.objects.filter(
            venta__fecha_venta__gte=self.inicio_dia,
            venta__estado='COMPLETADA'
        ).values(
            'producto__id',
            'producto__nombre',
            'producto__tipo_inventario'
        ).annotate(
            total_vendido=Sum('total'),
            cantidad_ventas=Count('id')
        ).order_by('-total_vendido')[:limite]
        
        return list(productos_dia)
    
    def get_ventas_por_categoria(self):
        """
        Ventas del día agrupadas por categoría
        """
        ventas_cat = DetalleVenta.objects.filter(
            venta__fecha_venta__gte=self.inicio_dia,
            venta__estado='COMPLETADA'
        ).values(
            'producto__categoria__nombre'
        ).annotate(
            total=Sum('total'),
            cantidad=Count('id'),
            total_costos=Sum('costo_total')  # ✅ Agregamos costos por separado
        ).order_by('-total')
        
        # Calcular utilidad en Python
        resultados = []
        for item in ventas_cat:
            item['utilidad'] = (item['total'] or Decimal('0')) - (item['total_costos'] or Decimal('0'))
            resultados.append(item)
        
        return resultados
    
    def get_tendencias_semanales(self):
        """
        Tendencia de ventas de los últimos 7 días
        """
        hace_7_dias = self.inicio_dia - timedelta(days=7)
        
        ventas_diarias = Venta.objects.filter(
            fecha_venta__gte=hace_7_dias,
            estado='COMPLETADA'
        ).annotate(
            dia=TruncDate('fecha_venta')
        ).values('dia').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('dia')
        
        return list(ventas_diarias)
    
    def get_comparativas(self):
        """
        Comparativas entre períodos
        """
        # Mes actual vs mes anterior
        inicio_mes_anterior = (self.inicio_mes - timedelta(days=1)).replace(day=1)
        
        ventas_mes_actual = Venta.objects.filter(
            fecha_venta__gte=self.inicio_mes,
            estado='COMPLETADA'
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))
        
        ventas_mes_anterior = Venta.objects.filter(
            fecha_venta__gte=inicio_mes_anterior,
            fecha_venta__lt=self.inicio_mes,
            estado='COMPLETADA'
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))
        
        variacion_mensual = (
            ((ventas_mes_actual['total'] - ventas_mes_anterior['total']) / 
             ventas_mes_anterior['total'] * 100)
            if ventas_mes_anterior['total'] > 0 else Decimal('0')
        )
        
        return {
            'mes_actual': ventas_mes_actual['total'],
            'mes_anterior': ventas_mes_anterior['total'],
            'variacion_porcentaje': variacion_mensual.quantize(Decimal('0.01'))
        }