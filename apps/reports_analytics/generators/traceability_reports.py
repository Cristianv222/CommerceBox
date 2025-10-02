# apps/reports_analytics/generators/traceability_reports.py

"""
Generador de reportes de trazabilidad
Seguimiento completo de quintales desde origen hasta venta
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from apps.inventory_management.models import (
    Quintal, MovimientoQuintal, Proveedor
)
from apps.sales_management.models import DetalleVenta


class TraceabilityReportGenerator:
    """
    Genera reportes de trazabilidad de quintales
    Sistema FIFO y seguimiento origen-destino
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
            self.fecha_desde = self.fecha_hasta - timedelta(days=90)
    
    def reporte_trazabilidad_quintal(self, quintal_id):
        """
        Trazabilidad completa de un quintal específico
        
        Args:
            quintal_id: UUID del quintal
        
        Returns:
            dict: Historia completa del quintal
        """
        try:
            quintal = Quintal.objects.select_related(
                'producto',
                'proveedor',
                'unidad_medida',
                'usuario_registro'
            ).get(id=quintal_id)
        except Quintal.DoesNotExist:
            return {'error': 'Quintal no encontrado'}
        
        # Información básica
        info_basica = {
            'codigo': quintal.codigo_unico,
            'producto': quintal.producto.nombre,
            'categoria': quintal.producto.categoria.nombre,
            'proveedor': {
                'nombre': quintal.proveedor.nombre_comercial,
                'ruc': quintal.proveedor.ruc_nit,
                'telefono': quintal.proveedor.telefono
            },
            'origen': quintal.origen,
            'lote': quintal.lote_proveedor,
            'factura_compra': quintal.numero_factura_compra,
            'fecha_recepcion': quintal.fecha_recepcion,
            'fecha_vencimiento': quintal.fecha_vencimiento,
            'usuario_registro': quintal.usuario_registro.get_full_name()
        }
        
        # Estado actual
        estado_actual = {
            'estado': quintal.get_estado_display(),
            'peso_inicial': quintal.peso_inicial,
            'peso_actual': quintal.peso_actual,
            'peso_vendido': quintal.peso_vendido(),
            'porcentaje_restante': quintal.porcentaje_restante(),
            'unidad': quintal.unidad_medida.abreviatura,
            'costo_total': quintal.costo_total,
            'costo_por_unidad': quintal.costo_por_unidad,
            'valor_restante': quintal.peso_actual * quintal.costo_por_unidad
        }
        
        # Historial de movimientos
        movimientos = MovimientoQuintal.objects.filter(
            quintal=quintal
        ).select_related('usuario', 'venta').order_by('fecha_movimiento')
        
        movimientos_data = []
        for mov in movimientos:
            movimientos_data.append({
                'fecha': mov.fecha_movimiento,
                'tipo': mov.get_tipo_movimiento_display(),
                'peso_movimiento': mov.peso_movimiento,
                'peso_antes': mov.peso_antes,
                'peso_despues': mov.peso_despues,
                'usuario': mov.usuario.get_full_name(),
                'venta': mov.venta.numero_venta if mov.venta else None,
                'observaciones': mov.observaciones
            })
        
        # Ventas asociadas
        ventas = DetalleVenta.objects.filter(
            quintal=quintal,
            venta__estado='COMPLETADA'
        ).select_related('venta', 'venta__cliente', 'venta__vendedor')
        
        ventas_data = []
        for venta in ventas:
            ventas_data.append({
                'numero_venta': venta.venta.numero_venta,
                'fecha': venta.venta.fecha_venta,
                'peso_vendido': venta.peso_vendido,
                'precio_unitario': venta.precio_por_unidad_peso,
                'total': venta.total,
                'cliente': (
                    venta.venta.cliente.nombre_completo() 
                    if venta.venta.cliente else 'Cliente General'
                ),
                'vendedor': venta.venta.vendedor.get_full_name()
            })
        
        # Cálculo de rentabilidad
        total_vendido = sum(v['total'] for v in ventas_data)
        costo_vendido = sum(
            v['peso_vendido'] * quintal.costo_por_unidad 
            for v in ventas_data
        )
        utilidad = total_vendido - costo_vendido
        margen = (
            (utilidad / total_vendido * 100) 
            if total_vendido > 0 else Decimal('0')
        )
        
        return {
            'informacion_basica': info_basica,
            'estado_actual': estado_actual,
            'movimientos': movimientos_data,
            'ventas': ventas_data,
            'rentabilidad': {
                'total_vendido': total_vendido,
                'costo_vendido': costo_vendido,
                'utilidad': utilidad,
                'margen_porcentaje': margen.quantize(Decimal('0.01'))
            },
            'estadisticas': {
                'total_movimientos': len(movimientos_data),
                'total_ventas': len(ventas_data),
                'dias_en_inventario': (
                    (timezone.now().date() - quintal.fecha_recepcion.date()).days
                    if quintal.fecha_recepcion else 0
                )
            }
        }
    
    def reporte_trazabilidad_por_lote(self, lote_proveedor):
        """
        Trazabilidad de todos los quintales de un lote
        
        Args:
            lote_proveedor: Número de lote del proveedor
        
        Returns:
            dict: Información de todos los quintales del lote
        """
        quintales = Quintal.objects.filter(
            lote_proveedor=lote_proveedor
        ).select_related('producto', 'proveedor')
        
        if not quintales.exists():
            return {'error': 'No se encontraron quintales con ese lote'}
        
        quintales_data = []
        for quintal in quintales:
            # Resumen de cada quintal
            ventas_quintal = DetalleVenta.objects.filter(
                quintal=quintal,
                venta__estado='COMPLETADA'
            ).aggregate(
                total_vendido=Coalesce(Sum('total'), Decimal('0')),
                peso_vendido=Coalesce(Sum('peso_vendido'), Decimal('0'))
            )
            
            quintales_data.append({
                'codigo': quintal.codigo_unico,
                'estado': quintal.get_estado_display(),
                'peso_inicial': quintal.peso_inicial,
                'peso_actual': quintal.peso_actual,
                'peso_vendido': ventas_quintal['peso_vendido'],
                'total_vendido': ventas_quintal['total_vendido'],
                'fecha_recepcion': quintal.fecha_recepcion
            })
        
        # Información del lote
        primer_quintal = quintales.first()
        
        # Totales del lote
        totales = quintales.aggregate(
            peso_total_inicial=Sum('peso_inicial'),
            peso_total_actual=Sum('peso_actual'),
            disponibles=Count('id', filter=Q(estado='DISPONIBLE')),
            agotados=Count('id', filter=Q(estado='AGOTADO'))
        )
        
        return {
            'lote': {
                'numero': lote_proveedor,
                'producto': primer_quintal.producto.nombre,
                'proveedor': primer_quintal.proveedor.nombre_comercial,
                'fecha_recepcion': primer_quintal.fecha_recepcion,
                'origen': primer_quintal.origen
            },
            'totales': {
                'cantidad_quintales': quintales.count(),
                'disponibles': totales['disponibles'],
                'agotados': totales['agotados'],
                'peso_total_inicial': totales['peso_total_inicial'],
                'peso_total_actual': totales['peso_total_actual']
            },
            'quintales': quintales_data
        }
    
    def reporte_trazabilidad_por_proveedor(self, proveedor_id):
        """
        Análisis de trazabilidad de quintales de un proveedor
        
        Args:
            proveedor_id: UUID del proveedor
        
        Returns:
            dict: Análisis completo del proveedor
        """
        try:
            proveedor = Proveedor.objects.get(id=proveedor_id)
        except Proveedor.DoesNotExist:
            return {'error': 'Proveedor no encontrado'}
        
        # Quintales del proveedor
        quintales = Quintal.objects.filter(
            proveedor=proveedor,
            fecha_recepcion__date__gte=self.fecha_desde,
            fecha_recepcion__date__lte=self.fecha_hasta
        ).select_related('producto')
        
        # Estadísticas generales
        stats = quintales.aggregate(
            total_quintales=Count('id'),
            disponibles=Count('id', filter=Q(estado='DISPONIBLE')),
            agotados=Count('id', filter=Q(estado='AGOTADO')),
            peso_total_recibido=Coalesce(Sum('peso_inicial'), Decimal('0')),
            peso_total_actual=Coalesce(Sum('peso_actual'), Decimal('0')),
            valor_total_compras=Coalesce(Sum('costo_total'), Decimal('0'))
        )
        
        # Quintales por producto
        por_producto = quintales.values(
            'producto__nombre',
            'producto__categoria__nombre'
        ).annotate(
            cantidad=Count('id'),
            peso_recibido=Sum('peso_inicial'),
            peso_actual=Sum('peso_actual'),
            valor_compras=Sum('costo_total')
        ).order_by('-peso_recibido')
        
        # Rendimiento de ventas
        ventas = DetalleVenta.objects.filter(
            quintal__proveedor=proveedor,
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA'
        ).aggregate(
            total_vendido=Coalesce(Sum('total'), Decimal('0')),
            peso_vendido=Coalesce(Sum('peso_vendido'), Decimal('0'))
        )
        
        # Cálculo de rentabilidad
        utilidad = ventas['total_vendido'] - stats['valor_total_compras']
        margen = (
            (utilidad / ventas['total_vendido'] * 100)
            if ventas['total_vendido'] > 0 else Decimal('0')
        )
        
        # Tiempo promedio de rotación
        quintales_agotados = quintales.filter(estado='AGOTADO')
        if quintales_agotados.exists():
            dias_rotacion = []
            for q in quintales_agotados:
                # Buscar última venta del quintal
                ultima_venta = DetalleVenta.objects.filter(
                    quintal=q,
                    venta__estado='COMPLETADA'
                ).order_by('-venta__fecha_venta').first()
                
                if ultima_venta:
                    dias = (ultima_venta.venta.fecha_venta.date() - q.fecha_recepcion.date()).days
                    dias_rotacion.append(dias)
            
            promedio_rotacion = (
                sum(dias_rotacion) / len(dias_rotacion) 
                if dias_rotacion else 0
            )
        else:
            promedio_rotacion = 0
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'proveedor': {
                'nombre': proveedor.nombre_comercial,
                'ruc': proveedor.ruc_nit,
                'telefono': proveedor.telefono,
                'email': proveedor.email
            },
            'estadisticas': {
                'total_quintales': stats['total_quintales'],
                'disponibles': stats['disponibles'],
                'agotados': stats['agotados'],
                'peso_total_recibido': stats['peso_total_recibido'],
                'peso_actual': stats['peso_total_actual'],
                'peso_vendido': ventas['peso_vendido'],
                'valor_compras': stats['valor_total_compras']
            },
            'por_producto': list(por_producto),
            'rendimiento': {
                'total_vendido': ventas['total_vendido'],
                'utilidad': utilidad.quantize(Decimal('0.01')),
                'margen_porcentaje': margen.quantize(Decimal('0.01')),
                'dias_rotacion_promedio': round(promedio_rotacion, 1)
            }
        }
    
    def reporte_flujo_fifo(self, producto_id):
        """
        Análisis del flujo FIFO de un producto
        
        Args:
            producto_id: UUID del producto
        
        Returns:
            dict: Análisis de cómo se está consumiendo el inventario
        """
        from apps.inventory_management.models import Producto
        
        try:
            producto = Producto.objects.get(id=producto_id, tipo_inventario='QUINTAL')
        except Producto.DoesNotExist:
            return {'error': 'Producto no encontrado o no es tipo quintal'}
        
        # Quintales disponibles ordenados por FIFO
        quintales_disponibles = Quintal.objects.filter(
            producto=producto,
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).select_related('proveedor').order_by('fecha_recepcion')
        
        quintales_data = []
        for quintal in quintales_disponibles:
            dias_inventario = (timezone.now().date() - quintal.fecha_recepcion.date()).days
            
            quintales_data.append({
                'codigo': quintal.codigo_unico,
                'proveedor': quintal.proveedor.nombre_comercial,
                'fecha_recepcion': quintal.fecha_recepcion,
                'dias_en_inventario': dias_inventario,
                'peso_inicial': quintal.peso_inicial,
                'peso_actual': quintal.peso_actual,
                'porcentaje_restante': quintal.porcentaje_restante(),
                'fecha_vencimiento': quintal.fecha_vencimiento,
                'orden_fifo': list(quintales_disponibles).index(quintal) + 1
            })
        
        # Análisis de ventas recientes
        ventas_recientes = DetalleVenta.objects.filter(
            producto=producto,
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__estado='COMPLETADA'
        ).select_related('quintal').order_by('-venta__fecha_venta')[:20]
        
        ventas_data = []
        for venta in ventas_recientes:
            ventas_data.append({
                'fecha': venta.venta.fecha_venta,
                'numero_venta': venta.venta.numero_venta,
                'quintal_usado': venta.quintal.codigo_unico if venta.quintal else 'N/A',
                'peso_vendido': venta.peso_vendido,
                'precio_unitario': venta.precio_por_unidad_peso
            })
        
        # Verificar cumplimiento FIFO
        # (verificar si se están usando los quintales más antiguos primero)
        violaciones_fifo = []
        
        for venta in ventas_recientes:
            if venta.quintal:
                # Buscar si había quintales más antiguos disponibles en ese momento
                quintales_anteriores = Quintal.objects.filter(
                    producto=producto,
                    fecha_recepcion__lt=venta.quintal.fecha_recepcion,
                    fecha_recepcion__lte=venta.venta.fecha_venta
                ).exclude(id=venta.quintal.id)
                
                # Verificar si tenían peso disponible
                for q_ant in quintales_anteriores:
                    # Buscar movimientos del quintal anterior hasta la fecha de la venta
                    mov_anterior = MovimientoQuintal.objects.filter(
                        quintal=q_ant,
                        fecha_movimiento__lte=venta.venta.fecha_venta
                    ).order_by('-fecha_movimiento').first()
                    
                    if mov_anterior and mov_anterior.peso_despues > 0:
                        violaciones_fifo.append({
                            'fecha_venta': venta.venta.fecha_venta,
                            'numero_venta': venta.venta.numero_venta,
                            'quintal_usado': venta.quintal.codigo_unico,
                            'quintal_que_debia_usarse': q_ant.codigo_unico,
                            'diferencia_dias': (venta.quintal.fecha_recepcion - q_ant.fecha_recepcion).days
                        })
                        break
        
        return {
            'producto': {
                'nombre': producto.nombre,
                'categoria': producto.categoria.nombre
            },
            'periodo_analisis': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'quintales_disponibles': {
                'items': quintales_data,
                'total': len(quintales_data),
                'peso_total': sum(q['peso_actual'] for q in quintales_data)
            },
            'ventas_recientes': ventas_data,
            'cumplimiento_fifo': {
                'violaciones': violaciones_fifo,
                'total_violaciones': len(violaciones_fifo),
                'porcentaje_cumplimiento': (
                    ((len(ventas_data) - len(violaciones_fifo)) / len(ventas_data) * 100)
                    if len(ventas_data) > 0 else Decimal('100')
                ).quantize(Decimal('0.01'))
            }
        }
    
    def reporte_ciclo_vida_quintales(self):
        """
        Análisis del ciclo de vida completo de quintales
        """
        # Quintales del período
        quintales = Quintal.objects.filter(
            fecha_recepcion__date__gte=self.fecha_desde,
            fecha_recepcion__date__lte=self.fecha_hasta
        ).select_related('producto', 'proveedor')
        
        # Clasificar por ciclo de vida
        analisis = {
            'nuevos_sin_vender': [],
            'en_venta_activa': [],
            'proximos_agotar': [],
            'agotados': []
        }
        
        for quintal in quintales:
            data = {
                'codigo': quintal.codigo_unico,
                'producto': quintal.producto.nombre,
                'proveedor': quintal.proveedor.nombre_comercial,
                'fecha_recepcion': quintal.fecha_recepcion,
                'peso_inicial': quintal.peso_inicial,
                'peso_actual': quintal.peso_actual,
                'dias_inventario': (timezone.now().date() - quintal.fecha_recepcion.date()).days
            }
            
            # Contar ventas
            num_ventas = DetalleVenta.objects.filter(
                quintal=quintal,
                venta__estado='COMPLETADA'
            ).count()
            
            data['ventas_realizadas'] = num_ventas
            
            if quintal.estado == 'AGOTADO':
                analisis['agotados'].append(data)
            elif num_ventas == 0:
                analisis['nuevos_sin_vender'].append(data)
            elif quintal.porcentaje_restante() <= 10:
                analisis['proximos_agotar'].append(data)
            else:
                analisis['en_venta_activa'].append(data)
        
        # Estadísticas
        total = quintales.count()
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'total_quintales': total,
            'analisis_ciclo_vida': {
                'nuevos_sin_vender': {
                    'items': analisis['nuevos_sin_vender'],
                    'cantidad': len(analisis['nuevos_sin_vender']),
                    'porcentaje': (
                        (len(analisis['nuevos_sin_vender']) / total * 100)
                        if total > 0 else 0
                    )
                },
                'en_venta_activa': {
                    'items': analisis['en_venta_activa'],
                    'cantidad': len(analisis['en_venta_activa']),
                    'porcentaje': (
                        (len(analisis['en_venta_activa']) / total * 100)
                        if total > 0 else 0
                    )
                },
                'proximos_agotar': {
                    'items': analisis['proximos_agotar'],
                    'cantidad': len(analisis['proximos_agotar']),
                    'porcentaje': (
                        (len(analisis['proximos_agotar']) / total * 100)
                        if total > 0 else 0
                    )
                },
                'agotados': {
                    'items': analisis['agotados'],
                    'cantidad': len(analisis['agotados']),
                    'porcentaje': (
                        (len(analisis['agotados']) / total * 100)
                        if total > 0 else 0
                    )
                }
            }
        }