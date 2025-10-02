# apps/reports_analytics/generators/financial_reports.py

"""
Generador de reportes financieros
Análisis de caja, flujo de efectivo, rentabilidad
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from datetime import timedelta

from apps.financial_management.models import (
    Caja, MovimientoCaja, ArqueoCaja, CajaChica, MovimientoCajaChica
)
from apps.sales_management.models import Venta, DetalleVenta
from apps.financial_management.accounting.cost_calculator import CostCalculator


class FinancialReportGenerator:
    """
    Genera reportes financieros y de caja
    """
    
    def __init__(self, fecha_desde=None, fecha_hasta=None):
        """
        Args:
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período
        """
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta or timezone.now().date()
        
        if not self.fecha_desde:
            self.fecha_desde = self.fecha_hasta - timedelta(days=30)
    
    def reporte_movimientos_caja(self, caja_id=None):
        """
        Reporte de movimientos de caja del período
        
        Args:
            caja_id: ID de caja específica (opcional)
        
        Returns:
            dict: Movimientos de caja detallados
        """
        # Filtro base
        filtros = {
            'fecha_movimiento__date__gte': self.fecha_desde,
            'fecha_movimiento__date__lte': self.fecha_hasta
        }
        
        if caja_id:
            filtros['caja__id'] = caja_id
        
        movimientos = MovimientoCaja.objects.filter(
            **filtros
        ).select_related('caja', 'usuario', 'venta').order_by('fecha_movimiento')
        
        # Agrupar por tipo
        por_tipo = movimientos.values('tipo_movimiento').annotate(
            cantidad=Count('id'),
            total=Sum('monto')
        ).order_by('-total')
        
        # Calcular totales
        totales = movimientos.aggregate(
            total_ingresos=Coalesce(Sum('monto', filter=Q(
                tipo_movimiento__in=['APERTURA', 'VENTA', 'INGRESO', 'AJUSTE_POSITIVO', 'TRANSFERENCIA_ENTRADA']
            )), Decimal('0')),
            total_egresos=Coalesce(Sum('monto', filter=Q(
                tipo_movimiento__in=['RETIRO', 'AJUSTE_NEGATIVO', 'TRANSFERENCIA_SALIDA']
            )), Decimal('0'))
        )
        
        # Detalle de movimientos
        movimientos_data = []
        for mov in movimientos:
            movimientos_data.append({
                'fecha': mov.fecha_movimiento,
                'caja': mov.caja.nombre,
                'tipo': mov.get_tipo_movimiento_display(),
                'monto': mov.monto,
                'saldo_anterior': mov.saldo_anterior,
                'saldo_nuevo': mov.saldo_nuevo,
                'usuario': mov.usuario.get_full_name(),
                'referencia': mov.venta.numero_venta if mov.venta else None,
                'observaciones': mov.observaciones
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'totales': {
                'ingresos': totales['total_ingresos'],
                'egresos': totales['total_egresos'],
                'neto': totales['total_ingresos'] - totales['total_egresos']
            },
            'por_tipo': list(por_tipo),
            'movimientos': movimientos_data,
            'total_movimientos': len(movimientos_data)
        }
    
    def reporte_arqueos_caja(self):
        """
        Análisis de arqueos de caja
        """
        arqueos = ArqueoCaja.objects.filter(
            fecha_cierre__date__gte=self.fecha_desde,
            fecha_cierre__date__lte=self.fecha_hasta
        ).select_related('caja', 'usuario_apertura', 'usuario_cierre').order_by('-fecha_cierre')
        
        arqueos_data = []
        for arq in arqueos:
            arqueos_data.append({
                'numero': arq.numero_arqueo,
                'caja': arq.caja.nombre,
                'fecha_apertura': arq.fecha_apertura,
                'fecha_cierre': arq.fecha_cierre,
                'monto_apertura': arq.monto_apertura,
                'total_ventas': arq.total_ventas,
                'total_ingresos': arq.total_ingresos,
                'total_retiros': arq.total_retiros,
                'monto_esperado': arq.monto_esperado,
                'monto_contado': arq.monto_contado,
                'diferencia': arq.diferencia,
                'estado': arq.get_estado_display(),
                'usuario_apertura': arq.usuario_apertura.get_full_name(),
                'usuario_cierre': arq.usuario_cierre.get_full_name()
            })
        
        # Estadísticas
        totales = arqueos.aggregate(
            total_ventas=Coalesce(Sum('total_ventas'), Decimal('0')),
            total_diferencias=Coalesce(Sum('diferencia'), Decimal('0')),
            cuadrados=Count('id', filter=Q(estado='CUADRADO')),
            sobrantes=Count('id', filter=Q(estado='SOBRANTE')),
            faltantes=Count('id', filter=Q(estado='FALTANTE'))
        )
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'arqueos': arqueos_data,
            'total_arqueos': len(arqueos_data),
            'estadisticas': {
                'total_ventas': totales['total_ventas'],
                'total_diferencias': totales['total_diferencias'],
                'cuadrados': totales['cuadrados'],
                'sobrantes': totales['sobrantes'],
                'faltantes': totales['faltantes'],
                'porcentaje_cuadrados': (
                    (totales['cuadrados'] / len(arqueos_data) * 100)
                    if len(arqueos_data) > 0 else Decimal('0')
                ).quantize(Decimal('0.01'))
            }
        }
    
    def reporte_caja_chica(self):
        """
        Análisis de caja chica
        """
        movimientos = MovimientoCajaChica.objects.filter(
            fecha_movimiento__date__gte=self.fecha_desde,
            fecha_movimiento__date__lte=self.fecha_hasta
        ).select_related('caja_chica', 'usuario').order_by('-fecha_movimiento')
        
        # Gastos por categoría
        gastos_categoria = movimientos.filter(
            tipo_movimiento='GASTO'
        ).values('categoria_gasto').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        ).order_by('-total')
        
        # Totales
        totales = movimientos.aggregate(
            gastos=Coalesce(Sum('monto', filter=Q(tipo_movimiento='GASTO')), Decimal('0')),
            reposiciones=Coalesce(Sum('monto', filter=Q(tipo_movimiento='REPOSICION')), Decimal('0'))
        )
        
        # Detalle de movimientos
        movimientos_data = []
        for mov in movimientos:
            movimientos_data.append({
                'fecha': mov.fecha_movimiento,
                'caja_chica': mov.caja_chica.nombre,
                'tipo': mov.get_tipo_movimiento_display(),
                'categoria': mov.get_categoria_gasto_display() if mov.categoria_gasto else None,
                'monto': mov.monto,
                'saldo_anterior': mov.saldo_anterior,
                'saldo_nuevo': mov.saldo_nuevo,
                'descripcion': mov.descripcion,
                'comprobante': mov.numero_comprobante,
                'usuario': mov.usuario.get_full_name()
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'totales': {
                'gastos': totales['gastos'],
                'reposiciones': totales['reposiciones']
            },
            'gastos_por_categoria': list(gastos_categoria),
            'movimientos': movimientos_data,
            'total_movimientos': len(movimientos_data)
        }
    
    def reporte_rentabilidad_periodo(self):
        """
        Análisis de rentabilidad del período
        """
        # Ventas y costos
        detalles = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).aggregate(
            ventas_totales=Coalesce(Sum('total'), Decimal('0')),
            costos_totales=Coalesce(Sum('costo_total'), Decimal('0')),
            descuentos_totales=Coalesce(Sum('descuento_monto'), Decimal('0'))
        )
        
        # Utilidad bruta
        utilidad_bruta = detalles['ventas_totales'] - detalles['costos_totales']
        margen_bruto = (
            (utilidad_bruta / detalles['ventas_totales'] * 100)
            if detalles['ventas_totales'] > 0 else Decimal('0')
        )
        
        # Gastos de caja chica (gastos operativos)
        gastos_operativos = MovimientoCajaChica.objects.filter(
            fecha_movimiento__date__gte=self.fecha_desde,
            fecha_movimiento__date__lte=self.fecha_hasta,
            tipo_movimiento='GASTO'
        ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))['total']
        
        # Utilidad neta (aproximada, sin incluir todos los gastos fijos)
        utilidad_neta = utilidad_bruta - gastos_operativos
        margen_neto = (
            (utilidad_neta / detalles['ventas_totales'] * 100)
            if detalles['ventas_totales'] > 0 else Decimal('0')
        )
        
        # ROI (Return on Investment) basado en inventario
        from apps.inventory_management.services.stock_service import StockService
        valor_inventario = StockService.calcular_valor_inventario()['valor_total']
        
        roi = (
            (utilidad_neta / valor_inventario * 100)
            if valor_inventario > 0 else Decimal('0')
        )
        
        # Rentabilidad por tipo de producto
        por_tipo = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values('producto__tipo_inventario').annotate(
            ventas=Sum('total'),
            costos=Sum('costo_total')
        ).annotate(
            utilidad=ExpressionWrapper(
                F('ventas') - F('costos'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            margen=ExpressionWrapper(
                ((F('ventas') - F('costos')) / F('ventas') * 100),
                output_field=DecimalField(max_digits=5, decimal_places=2)
            )
        )
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta,
                'dias': (self.fecha_hasta - self.fecha_desde).days + 1
            },
            'ventas': {
                'total': detalles['ventas_totales'],
                'descuentos': detalles['descuentos_totales']
            },
            'costos': {
                'costos_productos': detalles['costos_totales'],
                'gastos_operativos': gastos_operativos,
                'total': detalles['costos_totales'] + gastos_operativos
            },
            'utilidad': {
                'bruta': utilidad_bruta.quantize(Decimal('0.01')),
                'neta': utilidad_neta.quantize(Decimal('0.01')),
                'margen_bruto_porcentaje': margen_bruto.quantize(Decimal('0.01')),
                'margen_neto_porcentaje': margen_neto.quantize(Decimal('0.01'))
            },
            'roi': {
                'valor_inventario': valor_inventario,
                'roi_porcentaje': roi.quantize(Decimal('0.01'))
            },
            'por_tipo_producto': list(por_tipo)
        }
    
    def reporte_flujo_efectivo(self):
        """
        Análisis de flujo de efectivo del período
        """
        # Entradas (ventas en efectivo)
        from apps.sales_management.models import Pago
        
        entradas_efectivo = Pago.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            forma_pago='EFECTIVO'
        ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))['total']
        
        entradas_tarjeta = Pago.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            forma_pago__in=['TARJETA_DEBITO', 'TARJETA_CREDITO']
        ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))['total']
        
        # Salidas (gastos de caja chica)
        salidas = MovimientoCajaChica.objects.filter(
            fecha_movimiento__date__gte=self.fecha_desde,
            fecha_movimiento__date__lte=self.fecha_hasta,
            tipo_movimiento='GASTO'
        ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))['total']
        
        # Flujo neto
        flujo_neto = entradas_efectivo - salidas
        
        # Flujo por día
        flujo_diario = []
        fecha_actual = self.fecha_desde
        
        while fecha_actual <= self.fecha_hasta:
            entradas_dia = Pago.objects.filter(
                venta__fecha_venta__date=fecha_actual,
                venta__estado='COMPLETADA',
                forma_pago='EFECTIVO'
            ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))['total']
            
            salidas_dia = MovimientoCajaChica.objects.filter(
                fecha_movimiento__date=fecha_actual,
                tipo_movimiento='GASTO'
            ).aggregate(total=Coalesce(Sum('monto'), Decimal('0')))['total']
            
            flujo_diario.append({
                'fecha': fecha_actual,
                'entradas': entradas_dia,
                'salidas': salidas_dia,
                'neto': entradas_dia - salidas_dia
            })
            
            fecha_actual += timedelta(days=1)
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'resumen': {
                'entradas_efectivo': entradas_efectivo,
                'entradas_tarjeta': entradas_tarjeta,
                'total_entradas': entradas_efectivo + entradas_tarjeta,
                'salidas': salidas,
                'flujo_neto': flujo_neto
            },
            'flujo_diario': flujo_diario
        }
    
    def reporte_creditos_pendientes(self):
        """
        Análisis de créditos pendientes de cobro
        """
        from apps.sales_management.models import Venta
        
        creditos = Venta.objects.filter(
            tipo_venta='CREDITO',
            estado='COMPLETADA'
        ).annotate(
            saldo_pendiente=ExpressionWrapper(
                F('total') - F('monto_pagado'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).filter(saldo_pendiente__gt=0).select_related('cliente', 'vendedor')
        
        # Agrupar por estado de vencimiento
        hoy = timezone.now().date()
        
        vencidos = []
        por_vencer = []
        vigentes = []
        
        for credito in creditos:
            data = {
                'numero_venta': credito.numero_venta,
                'fecha_venta': credito.fecha_venta.date(),
                'fecha_vencimiento': credito.fecha_vencimiento,
                'cliente': credito.cliente.nombre_completo() if credito.cliente else 'Cliente General',
                'total': credito.total,
                'pagado': credito.monto_pagado,
                'saldo': credito.saldo_pendiente,
                'vendedor': credito.vendedor.get_full_name()
            }
            
            if credito.fecha_vencimiento:
                dias_vencimiento = (credito.fecha_vencimiento - hoy).days
                
                if dias_vencimiento < 0:
                    data['dias_vencido'] = abs(dias_vencimiento)
                    vencidos.append(data)
                elif dias_vencimiento <= 7:
                    data['dias_restantes'] = dias_vencimiento
                    por_vencer.append(data)
                else:
                    data['dias_restantes'] = dias_vencimiento
                    vigentes.append(data)
        
        # Totales
        total_vencidos = sum(c['saldo'] for c in vencidos)
        total_por_vencer = sum(c['saldo'] for c in por_vencer)
        total_vigentes = sum(c['saldo'] for c in vigentes)
        
        return {
            'fecha_corte': hoy,
            'resumen': {
                'vencidos': {
                    'cantidad': len(vencidos),
                    'monto': total_vencidos
                },
                'por_vencer': {
                    'cantidad': len(por_vencer),
                    'monto': total_por_vencer
                },
                'vigentes': {
                    'cantidad': len(vigentes),
                    'monto': total_vigentes
                },
                'total_cartera': total_vencidos + total_por_vencer + total_vigentes
            },
            'detalle': {
                'vencidos': vencidos,
                'por_vencer': por_vencer,
                'vigentes': vigentes
            }
        }
    
    def reporte_estado_financiero(self):
        """
        Estado financiero resumido (balance simplificado)
        """
        # Activos
        from apps.inventory_management.services.stock_service import StockService
        valor_inventario = StockService.calcular_valor_inventario()['valor_total']
        
        # Efectivo en caja
        cajas_abiertas = Caja.objects.filter(estado='ABIERTA').aggregate(
            total=Coalesce(Sum('monto_actual'), Decimal('0'))
        )['total']
        
        # Cuentas por cobrar
        cuentas_cobrar = Venta.objects.filter(
            tipo_venta='CREDITO',
            estado='COMPLETADA'
        ).annotate(
            saldo=ExpressionWrapper(
                F('total') - F('monto_pagado'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).filter(saldo__gt=0).aggregate(
            total=Coalesce(Sum('saldo'), Decimal('0'))
        )['total']
        
        total_activos = valor_inventario + cajas_abiertas + cuentas_cobrar
        
        # Pasivos (para un sistema simplificado)
        # Aquí podrías agregar cuentas por pagar si las tienes
        total_pasivos = Decimal('0')  # Placeholder
        
        # Patrimonio = Activos - Pasivos
        patrimonio = total_activos - total_pasivos
        
        return {
            'fecha_corte': timezone.now().date(),
            'activos': {
                'inventario': valor_inventario,
                'efectivo_caja': cajas_abiertas,
                'cuentas_por_cobrar': cuentas_cobrar,
                'total': total_activos
            },
            'pasivos': {
                'cuentas_por_pagar': Decimal('0'),  # Placeholder
                'total': total_pasivos
            },
            'patrimonio': patrimonio
        }