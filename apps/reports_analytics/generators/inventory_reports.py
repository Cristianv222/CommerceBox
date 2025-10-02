# apps/reports_analytics/generators/inventory_reports.py

"""
Generador de reportes de inventario
Análisis detallado de quintales y productos normales
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from apps.inventory_management.models import (
    Producto, Quintal, ProductoNormal, Categoria, Proveedor,
    MovimientoQuintal, MovimientoInventario
)


class InventoryReportGenerator:
    """
    Genera reportes detallados de inventario
    """
    
    def __init__(self, fecha_desde=None, fecha_hasta=None):
        """
        Args:
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período
        """
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta or timezone.now().date()
    
    def reporte_inventario_valorizado(self):
        """
        Reporte completo de inventario con valorización
        
        Returns:
            dict: Inventario valorizado completo
        """
        # Quintales disponibles
        quintales = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).select_related('producto', 'proveedor', 'unidad_medida').annotate(
            valor_actual=ExpressionWrapper(
                F('peso_actual') * F('costo_por_unidad'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        
        quintales_data = []
        for quintal in quintales:
            quintales_data.append({
                'codigo': quintal.codigo_unico,
                'producto': quintal.producto.nombre,
                'categoria': quintal.producto.categoria.nombre,
                'proveedor': quintal.proveedor.nombre_comercial,
                'peso_inicial': quintal.peso_inicial,
                'peso_actual': quintal.peso_actual,
                'peso_vendido': quintal.peso_vendido(),
                'porcentaje_restante': quintal.porcentaje_restante(),
                'unidad': quintal.unidad_medida.abreviatura,
                'costo_por_unidad': quintal.costo_por_unidad,
                'valor_actual': quintal.valor_actual,
                'fecha_recepcion': quintal.fecha_recepcion,
                'fecha_vencimiento': quintal.fecha_vencimiento,
                'estado': 'Crítico' if quintal.esta_critico() else 'Normal'
            })
        
        # Productos normales
        productos_normales = ProductoNormal.objects.filter(
            producto__activo=True
        ).select_related('producto', 'producto__categoria').annotate(
            valor_stock=ExpressionWrapper(
                F('stock_actual') * F('costo_unitario'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        
        productos_data = []
        for prod in productos_normales:
            productos_data.append({
                'codigo': prod.producto.codigo_barras,
                'nombre': prod.producto.nombre,
                'categoria': prod.producto.categoria.nombre,
                'stock_actual': prod.stock_actual,
                'stock_minimo': prod.stock_minimo,
                'stock_maximo': prod.stock_maximo,
                'costo_unitario': prod.costo_unitario,
                'valor_stock': prod.valor_stock,
                'estado': prod.estado_stock(),
                'necesita_reorden': prod.necesita_reorden(),
                'fecha_vencimiento': prod.fecha_vencimiento
            })
        
        # Totales
        total_quintales = sum(q['valor_actual'] for q in quintales_data)
        total_productos = sum(p['valor_stock'] for p in productos_data)
        
        return {
            'fecha_reporte': timezone.now(),
            'quintales': {
                'items': quintales_data,
                'cantidad': len(quintales_data),
                'valor_total': total_quintales
            },
            'productos_normales': {
                'items': productos_data,
                'cantidad': len(productos_data),
                'valor_total': total_productos
            },
            'totales': {
                'cantidad_items': len(quintales_data) + len(productos_data),
                'valor_total': total_quintales + total_productos
            }
        }
    
    def reporte_por_categoria(self):
        """
        Análisis de inventario agrupado por categoría
        """
        categorias = Categoria.objects.filter(activa=True)
        
        reporte = []
        
        for cat in categorias:
            # Quintales de esta categoría
            quintales_cat = Quintal.objects.filter(
                producto__categoria=cat,
                estado='DISPONIBLE'
            ).aggregate(
                cantidad=Count('id'),
                peso_total=Coalesce(Sum('peso_actual'), Decimal('0')),
                valor_total=Coalesce(Sum(F('peso_actual') * F('costo_por_unidad')), Decimal('0'))
            )
            
            # Productos normales de esta categoría
            productos_cat = ProductoNormal.objects.filter(
                producto__categoria=cat,
                producto__activo=True
            ).aggregate(
                cantidad=Count('id'),
                stock_total=Coalesce(Sum('stock_actual'), 0),
                valor_total=Coalesce(Sum(F('stock_actual') * F('costo_unitario')), Decimal('0'))
            )
            
            reporte.append({
                'categoria': cat.nombre,
                'quintales': {
                    'cantidad': quintales_cat['cantidad'],
                    'peso_total': quintales_cat['peso_total'],
                    'valor': quintales_cat['valor_total']
                },
                'productos_normales': {
                    'cantidad': productos_cat['cantidad'],
                    'stock_total': productos_cat['stock_total'],
                    'valor': productos_cat['valor_total']
                },
                'valor_total_categoria': quintales_cat['valor_total'] + productos_cat['valor_total']
            })
        
        # Ordenar por valor total descendente
        reporte.sort(key=lambda x: x['valor_total_categoria'], reverse=True)
        
        return {
            'fecha_reporte': timezone.now(),
            'categorias': reporte,
            'total_categorias': len(reporte)
        }
    
    def reporte_productos_criticos(self):
        """
        Reporte de productos que requieren atención
        """
        # Quintales críticos (menos del 10%)
        quintales_criticos = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__lte=F('peso_inicial') * 0.1,
            peso_actual__gt=0
        ).select_related('producto', 'proveedor').annotate(
            porcentaje=ExpressionWrapper(
                (F('peso_actual') / F('peso_inicial')) * 100,
                output_field=DecimalField(max_digits=5, decimal_places=2)
            )
        )
        
        quintales_data = [{
            'codigo': q.codigo_unico,
            'producto': q.producto.nombre,
            'proveedor': q.proveedor.nombre_comercial,
            'peso_actual': q.peso_actual,
            'peso_inicial': q.peso_inicial,
            'porcentaje_restante': q.porcentaje,
            'unidad': q.unidad_medida.abreviatura
        } for q in quintales_criticos]
        
        # Productos normales en stock crítico
        productos_criticos = ProductoNormal.objects.filter(
            stock_actual__lte=F('stock_minimo'),
            stock_actual__gt=0
        ).select_related('producto', 'producto__categoria')
        
        productos_data = [{
            'codigo': p.producto.codigo_barras,
            'nombre': p.producto.nombre,
            'categoria': p.producto.categoria.nombre,
            'stock_actual': p.stock_actual,
            'stock_minimo': p.stock_minimo,
            'deficit': p.stock_minimo - p.stock_actual
        } for p in productos_criticos]
        
        # Productos agotados
        productos_agotados = ProductoNormal.objects.filter(
            stock_actual=0,
            producto__activo=True
        ).select_related('producto', 'producto__categoria')
        
        agotados_data = [{
            'codigo': p.producto.codigo_barras,
            'nombre': p.producto.nombre,
            'categoria': p.producto.categoria.nombre,
            'stock_minimo': p.stock_minimo,
            'fecha_ultima_salida': p.fecha_ultima_salida
        } for p in productos_agotados]
        
        # Próximos a vencer
        hoy = timezone.now().date()
        proximos_vencer = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=hoy + timedelta(days=7),
            fecha_vencimiento__gte=hoy
        ).select_related('producto').order_by('fecha_vencimiento')
        
        vencer_data = [{
            'codigo': q.codigo_unico,
            'producto': q.producto.nombre,
            'fecha_vencimiento': q.fecha_vencimiento,
            'dias_restantes': (q.fecha_vencimiento - hoy).days,
            'peso_actual': q.peso_actual,
            'unidad': q.unidad_medida.abreviatura
        } for q in proximos_vencer]
        
        return {
            'fecha_reporte': timezone.now(),
            'quintales_criticos': {
                'items': quintales_data,
                'cantidad': len(quintales_data)
            },
            'productos_criticos': {
                'items': productos_data,
                'cantidad': len(productos_data)
            },
            'productos_agotados': {
                'items': agotados_data,
                'cantidad': len(agotados_data)
            },
            'proximos_vencer': {
                'items': vencer_data,
                'cantidad': len(vencer_data)
            },
            'total_alertas': (
                len(quintales_data) + 
                len(productos_data) + 
                len(agotados_data) + 
                len(vencer_data)
            )
        }
    
    def reporte_movimientos_inventario(self):
        """
        Reporte de movimientos de inventario en el período
        """
        if not self.fecha_desde:
            self.fecha_desde = self.fecha_hasta - timedelta(days=30)
        
        # Movimientos de quintales
        movimientos_quintales = MovimientoQuintal.objects.filter(
            fecha_movimiento__date__gte=self.fecha_desde,
            fecha_movimiento__date__lte=self.fecha_hasta
        ).select_related('quintal', 'quintal__producto', 'usuario')
        
        quintales_movs = []
        for mov in movimientos_quintales:
            quintales_movs.append({
                'fecha': mov.fecha_movimiento,
                'tipo': mov.get_tipo_movimiento_display(),
                'quintal': mov.quintal.codigo_unico,
                'producto': mov.quintal.producto.nombre,
                'peso_movimiento': mov.peso_movimiento,
                'peso_antes': mov.peso_antes,
                'peso_despues': mov.peso_despues,
                'unidad': mov.unidad_medida.abreviatura,
                'usuario': mov.usuario.get_full_name(),
                'observaciones': mov.observaciones
            })
        
        # Movimientos de productos normales
        movimientos_productos = MovimientoInventario.objects.filter(
            fecha_movimiento__date__gte=self.fecha_desde,
            fecha_movimiento__date__lte=self.fecha_hasta
        ).select_related('producto_normal', 'producto_normal__producto', 'usuario')
        
        productos_movs = []
        for mov in movimientos_productos:
            productos_movs.append({
                'fecha': mov.fecha_movimiento,
                'tipo': mov.get_tipo_movimiento_display(),
                'producto': mov.producto_normal.producto.nombre,
                'cantidad': mov.cantidad,
                'stock_antes': mov.stock_antes,
                'stock_despues': mov.stock_despues,
                'costo_unitario': mov.costo_unitario,
                'costo_total': mov.costo_total,
                'usuario': mov.usuario.get_full_name(),
                'observaciones': mov.observaciones
            })
        
        # Resumen por tipo de movimiento
        resumen_quintales = movimientos_quintales.values('tipo_movimiento').annotate(
            cantidad=Count('id'),
            total_peso=Sum('peso_movimiento')
        )
        
        resumen_productos = movimientos_productos.values('tipo_movimiento').annotate(
            cantidad=Count('id'),
            total_cantidad=Sum('cantidad')
        )
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'movimientos_quintales': {
                'items': quintales_movs,
                'total': len(quintales_movs),
                'resumen': list(resumen_quintales)
            },
            'movimientos_productos': {
                'items': productos_movs,
                'total': len(productos_movs),
                'resumen': list(resumen_productos)
            }
        }
    
    def reporte_rotacion_inventario(self):
        """
        Análisis de rotación de inventario
        """
        if not self.fecha_desde:
            self.fecha_desde = self.fecha_hasta - timedelta(days=30)
        
        # Productos normales con ventas
        from apps.sales_management.models import DetalleVenta
        
        productos_vendidos = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=self.fecha_desde,
            venta__fecha_venta__date__lte=self.fecha_hasta,
            venta__estado='COMPLETADA',
            producto__tipo_inventario='NORMAL'
        ).values(
            'producto__id',
            'producto__nombre',
            'producto__categoria__nombre'
        ).annotate(
            cantidad_vendida=Sum('cantidad_unidades'),
            ventas_totales=Sum('total')
        )
        
        rotacion = []
        
        for item in productos_vendidos:
            try:
                producto = Producto.objects.get(id=item['producto__id'])
                inventario = producto.inventario_normal
                
                # Cálculo de rotación
                dias_periodo = (self.fecha_hasta - self.fecha_desde).days
                promedio_inventario = (inventario.stock_actual + inventario.stock_minimo) / 2
                
                if promedio_inventario > 0 and dias_periodo > 0:
                    rotacion_periodo = item['cantidad_vendida'] / promedio_inventario
                    rotacion_anual = (rotacion_periodo * 365) / dias_periodo
                else:
                    rotacion_anual = 0
                
                rotacion.append({
                    'producto': item['producto__nombre'],
                    'categoria': item['producto__categoria__nombre'],
                    'cantidad_vendida': item['cantidad_vendida'],
                    'ventas_totales': item['ventas_totales'],
                    'stock_actual': inventario.stock_actual,
                    'rotacion_anual': round(rotacion_anual, 2),
                    'clasificacion': (
                        'Alta rotación' if rotacion_anual >= 12 else
                        'Rotación media' if rotacion_anual >= 6 else
                        'Baja rotación'
                    )
                })
            except:
                continue
        
        # Ordenar por rotación
        rotacion.sort(key=lambda x: x['rotacion_anual'], reverse=True)
        
        return {
            'periodo': {
                'desde': self.fecha_desde,
                'hasta': self.fecha_hasta
            },
            'productos': rotacion,
            'total_productos': len(rotacion)
        }
    
    def reporte_por_proveedor(self):
        """
        Análisis de inventario por proveedor
        """
        proveedores = Proveedor.objects.filter(activo=True)
        
        reporte = []
        
        for prov in proveedores:
            # Quintales del proveedor
            quintales = Quintal.objects.filter(
                proveedor=prov,
                estado='DISPONIBLE'
            ).aggregate(
                cantidad=Count('id'),
                peso_total=Coalesce(Sum('peso_actual'), Decimal('0')),
                valor_total=Coalesce(Sum(F('peso_actual') * F('costo_por_unidad')), Decimal('0'))
            )
            
            # Productos del proveedor
            productos = Producto.objects.filter(
                proveedor=prov,
                tipo_inventario='NORMAL',
                activo=True
            ).count()
            
            reporte.append({
                'proveedor': prov.nombre_comercial,
                'ruc': prov.ruc_nit,
                'quintales': {
                    'cantidad': quintales['cantidad'],
                    'peso_total': quintales['peso_total'],
                    'valor': quintales['valor_total']
                },
                'productos_catalogo': productos,
                'contacto': {
                    'telefono': prov.telefono,
                    'email': prov.email
                }
            })
        
        # Ordenar por valor de quintales
        reporte.sort(key=lambda x: x['quintales']['valor'], reverse=True)
        
        return {
            'fecha_reporte': timezone.now(),
            'proveedores': reporte,
            'total_proveedores': len(reporte)
        }