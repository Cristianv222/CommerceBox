"""
Generador de reportes de ventas - VERSIÓN MEJORADA
Análisis completo de ventas, rentabilidad, clientes y vendedores
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, ExpressionWrapper, Max, Min
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncWeek, ExtractHour, ExtractWeekDay
from django.utils import timezone
from datetime import timedelta, datetime

from apps.sales_management.models import (
    Venta, DetalleVenta, Cliente, Pago, Devolucion
)
from apps.inventory_management.models import Producto, Categoria, Marca


class SalesReportGenerator:
    """
    Genera reportes de ventas y análisis comercial
    ✅ MEJORADO: Incluye análisis de IVA, márgenes y tendencias
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
    
    # ========================================================================
    # REPORTE GENERAL DEL PERÍODO
    # ========================================================================
    
    def reporte_ventas_periodo(self):
        """
        Reporte general de ventas del período
        ✅ MEJORADO: Incluye análisis de IVA y métodos de pago detallados
        
        Returns:
            dict: Análisis completo de ventas
        """
        # Ventas del período
        ventas = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        )
        
        # Métricas generales
        metricas = ventas.aggregate(
            total_ventas=Coalesce(Sum('total'), Decimal('0')),
            cantidad_ventas=Count('id'),
            total_descuentos=Coalesce(Sum('descuento'), Decimal('0')),
            total_iva=Coalesce(Sum('impuestos'), Decimal('0')),
            ticket_promedio=Coalesce(Avg('total'), Decimal('0')),
            venta_maxima=Coalesce(Max('total'), Decimal('0')),
            venta_minima=Coalesce(Min('total'), Decimal('0'))
        )
        
        # Calcular utilidad
        detalles = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).aggregate(
            ventas_totales=Coalesce(Sum('total'), Decimal('0')),
            costos_totales=Coalesce(Sum('costo_total'), Decimal('0')),
            subtotal_sin_iva=Coalesce(Sum('subtotal'), Decimal('0'))
        )
        
        utilidad_bruta = detalles['ventas_totales'] - detalles['costos_totales']
        margen_porcentaje = (
            (utilidad_bruta / detalles['ventas_totales'] * 100)
            if detalles['ventas_totales'] > 0 else Decimal('0')
        )
        
        # Ventas por tipo de producto
        ventas_quintales = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            producto__tipo_inventario='QUINTAL'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id'),
            peso_total=Coalesce(Sum('peso_vendido'), Decimal('0'))
        )
        
        ventas_normales = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            producto__tipo_inventario='NORMAL'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id'),
            unidades_totales=Coalesce(Sum('cantidad_unidades'), 0)
        )
        
        # Ventas por tipo (contado vs crédito)
        por_tipo = ventas.values('tipo_venta').annotate(
            total=Sum('total'),
            cantidad=Count('id'),
            porcentaje_iva=Avg('porcentaje_iva_aplicado')
        ).order_by('-total')
        
        # Formas de pago detalladas
        pagos = Pago.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values('forma_pago').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        ).order_by('-total')
        
        # Calcular porcentajes de formas de pago
        total_pagos = sum(p['total'] for p in pagos)
        for pago in pagos:
            pago['porcentaje'] = (
                (pago['total'] / total_pagos * 100).quantize(Decimal('0.01'))
                if total_pagos > 0 else Decimal('0')
            )
        
        # Análisis por marcas (TOP 10)
        ventas_por_marca = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            producto__marca__isnull=False
        ).values(
            'producto__marca__nombre'
        ).annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('-total')[:10]
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta,
                'dias': (self.fecha_hasta - self.fecha_desde).days + 1
            },
            'metricas_generales': {
                'total_ventas': metricas['total_ventas'],
                'cantidad_ventas': metricas['cantidad_ventas'],
                'ticket_promedio': metricas['ticket_promedio'].quantize(Decimal('0.01')),
                'venta_maxima': metricas['venta_maxima'],
                'venta_minima': metricas['venta_minima'],
                'total_descuentos': metricas['total_descuentos'],
                'total_iva_recaudado': metricas['total_iva']
            },
            'rentabilidad': {
                'ventas_totales': detalles['ventas_totales'],
                'costos_totales': detalles['costos_totales'],
                'utilidad_bruta': utilidad_bruta.quantize(Decimal('0.01')),
                'margen_porcentaje': margen_porcentaje.quantize(Decimal('0.01')),
                'subtotal_sin_iva': detalles['subtotal_sin_iva']
            },
            'por_tipo_producto': {
                'quintales': {
                    'total': ventas_quintales['total'],
                    'cantidad_items': ventas_quintales['cantidad'],
                    'peso_total': ventas_quintales['peso_total']
                },
                'productos_normales': {
                    'total': ventas_normales['total'],
                    'cantidad_items': ventas_normales['cantidad'],
                    'unidades_totales': ventas_normales['unidades_totales']
                }
            },
            'por_tipo_venta': list(por_tipo),
            'formas_pago': list(pagos),
            'top_marcas': list(ventas_por_marca)
        }
    
    # ========================================================================
    # VENTAS DIARIAS
    # ========================================================================
    
    def reporte_ventas_diarias(self):
        """
        Ventas desglosadas por día
        ✅ MEJORADO: Incluye análisis de tendencias y promedios móviles
        """
        ventas_diarias = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).annotate(
            dia=TruncDate('fecha_venta')
        ).values('dia').annotate(
            total_ventas=Sum('total'),
            cantidad_ventas=Count('id'),
            ticket_promedio=Avg('total'),
            total_iva=Sum('impuestos')
        ).order_by('dia')
        
        # Calcular utilidad por día
        resultado = []
        suma_movil_3_dias = []
        
        for idx, dia_data in enumerate(ventas_diarias):
            detalles_dia = DetalleVenta.objects.filter(
                venta__fecha_venta__date=dia_data['dia'],
                venta__estado='COMPLETADA'
            ).aggregate(
                costos=Coalesce(Sum('costo_total'), Decimal('0'))
            )
            
            utilidad = dia_data['total_ventas'] - detalles_dia['costos']
            margen = (
                (utilidad / dia_data['total_ventas'] * 100)
                if dia_data['total_ventas'] > 0 else Decimal('0')
            )
            
            # Promedio móvil de 3 días
            suma_movil_3_dias.append(float(dia_data['total_ventas']))
            if len(suma_movil_3_dias) > 3:
                suma_movil_3_dias.pop(0)
            promedio_movil = sum(suma_movil_3_dias) / len(suma_movil_3_dias)
            
            resultado.append({
                'fecha': dia_data['dia'],
                'total_ventas': dia_data['total_ventas'],
                'cantidad_ventas': dia_data['cantidad_ventas'],
                'ticket_promedio': dia_data['ticket_promedio'].quantize(Decimal('0.01')),
                'utilidad': utilidad.quantize(Decimal('0.01')),
                'margen_porcentaje': margen.quantize(Decimal('0.01')),
                'total_iva': dia_data['total_iva'],
                'promedio_movil_3d': Decimal(str(promedio_movil)).quantize(Decimal('0.01'))
            })
        
        # Calcular tendencia
        if len(resultado) >= 2:
            tendencia = (resultado[-1]['total_ventas'] - resultado[0]['total_ventas']) / len(resultado)
        else:
            tendencia = Decimal('0')
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'ventas_diarias': resultado,
            'total_dias': len(resultado),
            'tendencia_diaria': tendencia.quantize(Decimal('0.01'))
        }
    
    # ========================================================================
    # PRODUCTOS MÁS VENDIDOS
    # ========================================================================
    
    def reporte_productos_mas_vendidos(self, limite=20):
        """
        Top productos más vendidos
        ✅ MEJORADO: Incluye análisis por marca y categoría
        """
        productos = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values(
            'producto__id',
            'producto__nombre',
            'producto__tipo_inventario',
            'producto__categoria__nombre',
            'producto__marca__nombre'
        ).annotate(
            total_vendido=Sum('total'),
            cantidad_ventas=Count('id'),
            costo_total=Sum('costo_total'),
            cantidad_items=Sum('cantidad_unidades'),  # Para productos normales
            peso_total=Sum('peso_vendido')  # Para quintales
        ).annotate(
            utilidad=ExpressionWrapper(
                F('total_vendido') - F('costo_total'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            margen=ExpressionWrapper(
                ((F('total_vendido') - F('costo_total')) / F('total_vendido') * 100),
                output_field=DecimalField(max_digits=5, decimal_places=2)
            )
        ).order_by('-total_vendido')[:limite]
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'productos': list(productos),
            'total_productos': productos.count()
        }
    
    # ========================================================================
    # ANÁLISIS POR CATEGORÍA
    # ========================================================================
    
    def reporte_ventas_por_categoria(self):
        """
        Análisis de ventas por categoría
        ✅ MEJORADO: Incluye participación de mercado y tendencias
        """
        categorias = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values(
            'producto__categoria__id',
            'producto__categoria__nombre'
        ).annotate(
            total_ventas=Sum('total'),
            cantidad_items=Count('id'),
            costo_total=Sum('costo_total'),
            descuento_total=Sum('descuento_monto'),
            productos_distintos=Count('producto', distinct=True)
        ).annotate(
            utilidad=ExpressionWrapper(
                F('total_ventas') - F('costo_total'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            margen=ExpressionWrapper(
                ((F('total_ventas') - F('costo_total')) / F('total_ventas') * 100),
                output_field=DecimalField(max_digits=5, decimal_places=2)
            )
        ).order_by('-total_ventas')
        
        # Calcular porcentaje de participación
        total_general = sum(c['total_ventas'] for c in categorias)
        
        resultado = []
        for cat in categorias:
            participacion = (
                (cat['total_ventas'] / total_general * 100)
                if total_general > 0 else Decimal('0')
            )
            
            resultado.append({
                'categoria': cat['producto__categoria__nombre'],
                'total_ventas': cat['total_ventas'],
                'cantidad_items': cat['cantidad_items'],
                'productos_distintos': cat['productos_distintos'],
                'utilidad': cat['utilidad'],
                'margen_porcentaje': cat['margen'].quantize(Decimal('0.01')) if cat['margen'] else Decimal('0'),
                'participacion_porcentaje': participacion.quantize(Decimal('0.01'))
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'categorias': resultado,
            'total_categorias': len(resultado),
            'total_general': total_general
        }
    
    # ========================================================================
    # ANÁLISIS POR VENDEDOR
    # ========================================================================
    
    def reporte_ventas_por_vendedor(self):
        """
        Análisis de ventas por vendedor
        ✅ CORREGIDO: Usa 'nombres' y 'apellidos' en lugar de first_name/last_name
        """
        vendedores = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).values(
            'vendedor__id',
            'vendedor__nombres',      # ✅ CORREGIDO
            'vendedor__apellidos'      # ✅ CORREGIDO
        ).annotate(
            total_ventas=Sum('total'),
            cantidad_ventas=Count('id'),
            ticket_promedio=Avg('total'),
            total_iva=Sum('impuestos')
        ).order_by('-total_ventas')
        
        # Calcular utilidad por vendedor
        resultado = []
        for idx, vend in enumerate(vendedores, 1):
            detalles = DetalleVenta.objects.filter(
                venta__vendedor__id=vend['vendedor__id'],
                venta__fecha_venta__date__gte=self.fecha_desde,
                venta__fecha_venta__date__lte=self.fecha_hasta,
                venta__estado='COMPLETADA'
            ).aggregate(
                costos=Coalesce(Sum('costo_total'), Decimal('0'))
            )
            
            utilidad = vend['total_ventas'] - detalles['costos']
            margen = (
                (utilidad / vend['total_ventas'] * 100)
                if vend['total_ventas'] > 0 else Decimal('0')
            )
            
            resultado.append({
                'ranking': idx,
                'vendedor': f"{vend['vendedor__nombres']} {vend['vendedor__apellidos']}",  # ✅ CORREGIDO
                'total_ventas': vend['total_ventas'],
                'cantidad_ventas': vend['cantidad_ventas'],
                'ticket_promedio': vend['ticket_promedio'].quantize(Decimal('0.01')),
                'utilidad_generada': utilidad.quantize(Decimal('0.01')),
                'margen_porcentaje': margen.quantize(Decimal('0.01')),
                'total_iva_recaudado': vend['total_iva']
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'vendedores': resultado,
            'total_vendedores': len(resultado)
        }
    # ========================================================================
    # TOP CLIENTES
    # ========================================================================
    
    def reporte_clientes_top(self, limite=20):
        """
        Top clientes por volumen de compras
        ✅ MEJORADO: Incluye análisis de frecuencia y valor del cliente
        """
        clientes = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA',
            cliente__isnull=False
        ).values(
            'cliente__id',
            'cliente__nombres',
            'cliente__apellidos',
            'cliente__tipo_cliente',
            'cliente__numero_documento'
        ).annotate(
            total_compras=Sum('total'),
            cantidad_compras=Count('id'),
            ticket_promedio=Avg('total'),
            ultima_compra=Max('fecha_venta')
        ).order_by('-total_compras')[:limite]
        
        resultado = []
        for idx, cliente in enumerate(clientes, 1):
            # Calcular frecuencia de compra
            dias_periodo = (self.fecha_hasta - self.fecha_desde).days + 1
            frecuencia = cliente['cantidad_compras'] / dias_periodo if dias_periodo > 0 else 0
            
            # Calcular días desde última compra
            dias_ultima_compra = (timezone.now().date() - cliente['ultima_compra'].date()).days
            
            resultado.append({
                'ranking': idx,
                'cliente': f"{cliente['cliente__nombres']} {cliente['cliente__apellidos']}",
                'documento': cliente['cliente__numero_documento'],
                'tipo_cliente': cliente['cliente__tipo_cliente'],
                'total_compras': cliente['total_compras'],
                'cantidad_compras': cliente['cantidad_compras'],
                'ticket_promedio': cliente['ticket_promedio'].quantize(Decimal('0.01')),
                'frecuencia_compra': round(frecuencia, 2),
                'dias_ultima_compra': dias_ultima_compra
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'clientes': resultado,
            'total_clientes': len(resultado)
        }
    
    # ========================================================================
    # ANÁLISIS DE DEVOLUCIONES
    # ========================================================================
    
    def reporte_devoluciones(self):
        """
        Análisis de devoluciones
        ✅ MEJORADO: Incluye causas raíz y productos problemáticos
        """
        devoluciones = Devolucion.objects.filter(
            fecha_devolucion__date__gte=self.fecha_desde,
            fecha_devolucion__date__lte=self.fecha_hasta
        ).select_related('venta_original', 'detalle_venta__producto')
        
        # Agrupar por motivo
        por_motivo = devoluciones.values('motivo').annotate(
            cantidad=Count('id'),
            monto_total=Sum('monto_devolucion')
        ).order_by('-cantidad')
        
        # Agrupar por producto
        por_producto = devoluciones.values(
            'detalle_venta__producto__nombre'
        ).annotate(
            cantidad=Count('id'),
            monto_total=Sum('monto_devolucion')
        ).order_by('-cantidad')[:10]
        
        # Total de devoluciones
        totales = devoluciones.aggregate(
            cantidad_total=Count('id'),
            monto_total=Coalesce(Sum('monto_devolucion'), Decimal('0'))
        )
        
        # Calcular porcentaje respecto a ventas
        ventas_totales = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))
        
        porcentaje_devolucion = (
            (totales['monto_total'] / ventas_totales['total'] * 100)
            if ventas_totales['total'] > 0 else Decimal('0')
        )
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'resumen': {
                'cantidad_total': totales['cantidad_total'],
                'monto_total': totales['monto_total'],
                'porcentaje_ventas': porcentaje_devolucion.quantize(Decimal('0.01'))
            },
            'por_motivo': list(por_motivo),
            'por_producto': list(por_producto)
        }
    
    # ========================================================================
    # COMPARATIVO DE PERÍODOS
    # ========================================================================
    
    def reporte_comparativo_periodos(self, periodo_anterior_dias=None):
        """
        Comparación con período anterior
        ✅ CORREGIDO: Convierte correctamente a Decimal
        """
        from decimal import Decimal
        
        # Período actual
        dias = (self.fecha_hasta - self.fecha_desde).days + 1
        
        # Período anterior (mismo número de días)
        if not periodo_anterior_dias:
            periodo_anterior_dias = dias
        
        fecha_desde_anterior = self.fecha_desde - timedelta(days=periodo_anterior_dias)
        fecha_hasta_anterior = self.fecha_desde - timedelta(days=1)
        
        # Ventas período actual
        actual = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id'),
            total_iva=Coalesce(Sum('impuestos'), Decimal('0'))
        )
        
        # Calcular ticket promedio manualmente - CONVERTIR A DECIMAL
        if actual['cantidad'] > 0:
            actual['ticket_promedio'] = Decimal(str(float(actual['total']) / actual['cantidad']))
        else:
            actual['ticket_promedio'] = Decimal('0')
        
        # Ventas período anterior
        anterior = Venta.objects.filter(
            fecha_venta__date__gte=fecha_desde_anterior,
            fecha_venta__date__lte=fecha_hasta_anterior,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id'),
            total_iva=Coalesce(Sum('impuestos'), Decimal('0'))
        )
        
        # Calcular ticket promedio manualmente - CONVERTIR A DECIMAL
        if anterior['cantidad'] > 0:
            anterior['ticket_promedio'] = Decimal(str(float(anterior['total']) / anterior['cantidad']))
        else:
            anterior['ticket_promedio'] = Decimal('0')
        
        # Calcular variaciones
        variacion_total = (
            ((actual['total'] - anterior['total']) / anterior['total'] * 100)
            if anterior['total'] > 0 else Decimal('0')
        )
        
        variacion_cantidad = (
            ((Decimal(str(actual['cantidad'])) - Decimal(str(anterior['cantidad']))) / Decimal(str(anterior['cantidad'])) * 100)
            if anterior['cantidad'] > 0 else Decimal('0')
        )
        
        variacion_ticket = (
            ((actual['ticket_promedio'] - anterior['ticket_promedio']) / anterior['ticket_promedio'] * 100)
            if anterior['ticket_promedio'] > 0 else Decimal('0')
        )
        
        variacion_iva = (
            ((actual['total_iva'] - anterior['total_iva']) / anterior['total_iva'] * 100)
            if anterior['total_iva'] > 0 else Decimal('0')
        )
        
        return {
            'periodo_actual': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta,
                'total_ventas': actual['total'],
                'cantidad_ventas': actual['cantidad'],
                'ticket_promedio': actual['ticket_promedio'].quantize(Decimal('0.01')),
                'total_iva': actual['total_iva']
            },
            'periodo_anterior': {
                'desde': fecha_desde_anterior,
                'hasta': fecha_hasta_anterior,
                'total_ventas': anterior['total'],
                'cantidad_ventas': anterior['cantidad'],
                'ticket_promedio': anterior['ticket_promedio'].quantize(Decimal('0.01')),
                'total_iva': anterior['total_iva']
            },
            'variaciones': {
                'ventas_porcentaje': variacion_total.quantize(Decimal('0.01')),
                'cantidad_porcentaje': variacion_cantidad.quantize(Decimal('0.01')),
                'ticket_porcentaje': variacion_ticket.quantize(Decimal('0.01')),
                'iva_porcentaje': variacion_iva.quantize(Decimal('0.01'))
            }
        }
        
    # ========================================================================
    # ANÁLISIS DE HORARIOS
    # ========================================================================
    
    def reporte_horarios_ventas(self):
        """
        Análisis de ventas por hora del día y día de la semana
        ✅ CORREGIDO: Elimina Avg sobre campo agregado
        """
        # Ventas por hora
        ventas_por_hora = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).annotate(
            hora=ExtractHour('fecha_venta')
        ).values('hora').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('hora')
        
        # Calcular ticket promedio manualmente
        resultado_horas = []
        for item in ventas_por_hora:
            ticket_prom = (
                item['total'] / item['cantidad']
                if item['cantidad'] > 0 else Decimal('0')
            )
            resultado_horas.append({
                'hora': item['hora'],
                'total': item['total'],
                'cantidad': item['cantidad'],
                'ticket_promedio': ticket_prom.quantize(Decimal('0.01'))
            })
        
        # Ventas por día de la semana
        ventas_por_dia_semana = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).annotate(
            dia_semana=ExtractWeekDay('fecha_venta')
        ).values('dia_semana').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('dia_semana')
        
        # Mapear días de la semana
        dias_nombres = {
            1: 'Domingo',
            2: 'Lunes',
            3: 'Martes',
            4: 'Miércoles',
            5: 'Jueves',
            6: 'Viernes',
            7: 'Sábado'
        }
        
        resultado_dias = []
        for dia in ventas_por_dia_semana:
            resultado_dias.append({
                'dia_semana': dia['dia_semana'],
                'dia_nombre': dias_nombres.get(dia['dia_semana'], 'Desconocido'),
                'total': dia['total'],
                'cantidad': dia['cantidad']
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'ventas_por_hora': resultado_horas,
            'ventas_por_dia_semana': resultado_dias
        }
    
    # ========================================================================
    # ANÁLISIS DE MÁRGENES
    # ========================================================================
    
    def reporte_analisis_margenes(self):
        """
        Análisis detallado de márgenes de ganancia
        ✅ NUEVO: Identifica productos más y menos rentables
        """
        # Productos con mejor margen
        mejor_margen = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values(
            'producto__nombre'
        ).annotate(
            total_vendido=Sum('total'),
            costo_total=Sum('costo_total')
        ).annotate(
            margen=ExpressionWrapper(
                ((F('total_vendido') - F('costo_total')) / F('total_vendido') * 100),
                output_field=DecimalField(max_digits=5, decimal_places=2)
            )
        ).order_by('-margen')[:10]
        
        # Productos con peor margen (pero positivo)
        peor_margen = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values(
            'producto__nombre'
        ).annotate(
            total_vendido=Sum('total'),
            costo_total=Sum('costo_total')
        ).annotate(
            margen=ExpressionWrapper(
                ((F('total_vendido') - F('costo_total')) / F('total_vendido') * 100),
                output_field=DecimalField(max_digits=5, decimal_places=2)
            )
        ).filter(margen__gt=0).order_by('margen')[:10]
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'mejor_margen': list(mejor_margen),
            'peor_margen': list(peor_margen)
        }