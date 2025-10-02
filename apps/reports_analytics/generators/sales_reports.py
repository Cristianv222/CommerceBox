# apps/reports_analytics/generators/sales_reports.py

"""
Generador de reportes de ventas
Análisis de ventas, rentabilidad, clientes y vendedores
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta

from apps.sales_management.models import (
    Venta, DetalleVenta, Cliente, Pago, Devolucion
)
from apps.inventory_management.models import Producto, Categoria


class SalesReportGenerator:
    """
    Genera reportes de ventas y análisis comercial
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
    
    def reporte_ventas_periodo(self):
        """
        Reporte general de ventas del período
        
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
            ticket_promedio=Coalesce(Avg('total'), Decimal('0'))
        )
        
        # Calcular utilidad
        detalles = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).aggregate(
            ventas_totales=Coalesce(Sum('total'), Decimal('0')),
            costos_totales=Coalesce(Sum('costo_total'), Decimal('0'))
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
            cantidad=Count('id')
        )
        
        ventas_normales = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            producto__tipo_inventario='NORMAL'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id')
        )
        
        # Ventas por tipo (contado vs crédito)
        por_tipo = ventas.values('tipo_venta').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        )
        
        # Formas de pago
        pagos = Pago.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values('forma_pago').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        ).order_by('-total')
        
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
                'total_descuentos': metricas['total_descuentos']
            },
            'rentabilidad': {
                'ventas_totales': detalles['ventas_totales'],
                'costos_totales': detalles['costos_totales'],
                'utilidad_bruta': utilidad_bruta.quantize(Decimal('0.01')),
                'margen_porcentaje': margen_porcentaje.quantize(Decimal('0.01'))
            },
            'por_tipo_producto': {
                'quintales': ventas_quintales,
                'productos_normales': ventas_normales
            },
            'por_tipo_venta': list(por_tipo),
            'formas_pago': list(pagos)
        }
    
    def reporte_ventas_diarias(self):
        """
        Ventas desglosadas por día
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
            ticket_promedio=Avg('total')
        ).order_by('dia')
        
        # Calcular utilidad por día
        resultado = []
        for dia_data in ventas_diarias:
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
            
            resultado.append({
                'fecha': dia_data['dia'],
                'total_ventas': dia_data['total_ventas'],
                'cantidad_ventas': dia_data['cantidad_ventas'],
                'ticket_promedio': dia_data['ticket_promedio'].quantize(Decimal('0.01')),
                'utilidad': utilidad.quantize(Decimal('0.01')),
                'margen_porcentaje': margen.quantize(Decimal('0.01'))
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'ventas_diarias': resultado,
            'total_dias': len(resultado)
        }
    
    def reporte_productos_mas_vendidos(self, limite=20):
        """
        Top productos más vendidos
        """
        productos = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).values(
            'producto__id',
            'producto__nombre',
            'producto__tipo_inventario',
            'producto__categoria__nombre'
        ).annotate(
            total_vendido=Sum('total'),
            cantidad_ventas=Count('id'),
            costo_total=Sum('costo_total')
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
    
    def reporte_ventas_por_categoria(self):
        """
        Análisis de ventas por categoría
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
            descuento_total=Sum('descuento_monto')
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
            'total_categorias': len(resultado)
        }
    
    def reporte_ventas_por_vendedor(self):
        """
        Análisis de ventas por vendedor
        """
        vendedores = Venta.objects.filter(
            fecha_venta__date__gte=self.fecha_desde,
            fecha_venta__date__lte=self.fecha_hasta,
            estado='COMPLETADA'
        ).values(
            'vendedor__id',
            'vendedor__first_name',
            'vendedor__last_name'
        ).annotate(
            total_ventas=Sum('total'),
            cantidad_ventas=Count('id'),
            ticket_promedio=Avg('total')
        ).order_by('-total_ventas')
        
        # Calcular utilidad por vendedor
        resultado = []
        for vend in vendedores:
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
                'vendedor': f"{vend['vendedor__first_name']} {vend['vendedor__last_name']}",
                'total_ventas': vend['total_ventas'],
                'cantidad_ventas': vend['cantidad_ventas'],
                'ticket_promedio': vend['ticket_promedio'].quantize(Decimal('0.01')),
                'utilidad_generada': utilidad.quantize(Decimal('0.01')),
                'margen_porcentaje': margen.quantize(Decimal('0.01'))
            })
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'vendedores': resultado,
            'total_vendedores': len(resultado)
        }
    
    def reporte_clientes_top(self, limite=20):
        """
        Top clientes por volumen de compras
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
            'cliente__tipo_cliente'
        ).annotate(
            total_compras=Sum('total'),
            cantidad_compras=Count('id'),
            ticket_promedio=Avg('total')
        ).order_by('-total_compras')[:limite]
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'clientes': list(clientes),
            'total_clientes': clientes.count()
        }
    
    def reporte_devoluciones(self):
        """
        Análisis de devoluciones
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
        ).order_by('-cantidad')
        
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
    
    def reporte_comparativo_periodos(self, periodo_anterior_dias=None):
        """
        Comparación con período anterior
        """
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
            ticket_promedio=Coalesce(Avg('total'), Decimal('0'))
        )
        
        # Ventas período anterior
        anterior = Venta.objects.filter(
            fecha_venta__date__gte=fecha_desde_anterior,
            fecha_venta__date__lte=fecha_hasta_anterior,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id'),
            ticket_promedio=Coalesce(Avg('total'), Decimal('0'))
        )
        
        # Calcular variaciones
        variacion_total = (
            ((actual['total'] - anterior['total']) / anterior['total'] * 100)
            if anterior['total'] > 0 else Decimal('0')
        )
        
        variacion_cantidad = (
            ((actual['cantidad'] - anterior['cantidad']) / anterior['cantidad'] * 100)
            if anterior['cantidad'] > 0 else Decimal('0')
        )
        
        variacion_ticket = (
            ((actual['ticket_promedio'] - anterior['ticket_promedio']) / anterior['ticket_promedio'] * 100)
            if anterior['ticket_promedio'] > 0 else Decimal('0')
        )
        
        return {
            'periodo_actual': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta,
                'total_ventas': actual['total'],
                'cantidad_ventas': actual['cantidad'],
                'ticket_promedio': actual['ticket_promedio'].quantize(Decimal('0.01'))
            },
            'periodo_anterior': {
                'desde': fecha_desde_anterior,
                'hasta': fecha_hasta_anterior,
                'total_ventas': anterior['total'],
                'cantidad_ventas': anterior['cantidad'],
                'ticket_promedio': anterior['ticket_promedio'].quantize(Decimal('0.01'))
            },
            'variaciones': {
                'ventas_porcentaje': variacion_total.quantize(Decimal('0.01')),
                'cantidad_porcentaje': variacion_cantidad.quantize(Decimal('0.01')),
                'ticket_porcentaje': variacion_ticket.quantize(Decimal('0.01'))
            }
        }
    
    def reporte_horarios_ventas(self):
        """
        Análisis de ventas por hora del día
        """
        from django.db.models.functions import ExtractHour
        
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
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'ventas_por_hora': list(ventas_por_hora)
        }