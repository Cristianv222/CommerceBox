from django.db.models import Q
from ..models import Quintal, MovimientoQuintal, ProductoNormal, MovimientoInventario


class TraceabilityService:
    """
    Servicio para trazabilidad completa del inventario
    Permite rastrear el origen y destino de cada producto
    """
    
    @staticmethod
    def obtener_trazabilidad_quintal(quintal):
        """
        Obtiene trazabilidad completa de un quintal
        
        Args:
            quintal: Instancia de Quintal
        
        Returns:
            dict con información completa de trazabilidad
        """
        # Todos los movimientos
        movimientos = MovimientoQuintal.objects.filter(
            quintal=quintal
        ).select_related('usuario', 'venta').order_by('fecha_movimiento')
        
        # Ventas asociadas
        ventas = movimientos.filter(
            tipo_movimiento='VENTA',
            venta__isnull=False
        ).select_related('venta', 'venta__cliente')
        
        # Estadísticas
        total_vendido = sum(
            abs(m.peso_movimiento) for m in movimientos 
            if m.tipo_movimiento == 'VENTA'
        )
        
        return {
            'quintal': quintal,
            'origen': {
                'proveedor': quintal.proveedor.nombre_comercial,
                'lote': quintal.lote_proveedor,
                'factura': quintal.numero_factura_compra,
                'fecha_recepcion': quintal.fecha_recepcion,
                'origen_geografico': quintal.origen,
            },
            'estado_actual': {
                'peso_inicial': quintal.peso_inicial,
                'peso_actual': quintal.peso_actual,
                'peso_vendido': total_vendido,
                'porcentaje_restante': quintal.porcentaje_restante(),
                'estado': quintal.get_estado_display(),
            },
            'movimientos': list(movimientos),
            'total_movimientos': movimientos.count(),
            'ventas': list(ventas),
            'total_ventas': ventas.count(),
        }
    
    @staticmethod
    def obtener_trazabilidad_producto(producto):
        """
        Obtiene trazabilidad de un producto maestro
        
        Args:
            producto: Instancia de Producto
        
        Returns:
            dict con trazabilidad según tipo
        """
        if producto.es_quintal():
            return TraceabilityService._trazabilidad_producto_quintal(producto)
        else:
            return TraceabilityService._trazabilidad_producto_normal(producto)
    
    @staticmethod
    def _trazabilidad_producto_quintal(producto):
        """Trazabilidad para producto tipo QUINTAL"""
        quintales = Quintal.objects.filter(
            producto=producto
        ).select_related('proveedor').order_by('-fecha_recepcion')
        
        movimientos = MovimientoQuintal.objects.filter(
            quintal__producto=producto
        ).select_related('quintal', 'usuario').order_by('-fecha_movimiento')
        
        return {
            'producto': producto,
            'tipo': 'QUINTAL',
            'quintales': {
                'total': quintales.count(),
                'disponibles': quintales.filter(estado='DISPONIBLE').count(),
                'agotados': quintales.filter(estado='AGOTADO').count(),
                'listado': list(quintales[:20])
            },
            'movimientos_recientes': list(movimientos[:50]),
            'proveedores': list(set(q.proveedor for q in quintales))
        }
    
    @staticmethod
    def _trazabilidad_producto_normal(producto):
        """Trazabilidad para producto tipo NORMAL"""
        try:
            inventario = producto.inventario_normal
            
            movimientos = MovimientoInventario.objects.filter(
                producto_normal=inventario
            ).select_related('usuario', 'venta', 'compra').order_by('-fecha_movimiento')
            
            # Entradas y salidas
            entradas = movimientos.filter(cantidad__gt=0)
            salidas = movimientos.filter(cantidad__lt=0)
            
            return {
                'producto': producto,
                'tipo': 'NORMAL',
                'inventario': inventario,
                'movimientos_recientes': list(movimientos[:50]),
                'estadisticas': {
                    'total_entradas': sum(m.cantidad for m in entradas),
                    'total_salidas': abs(sum(m.cantidad for m in salidas)),
                    'stock_actual': inventario.stock_actual,
                    'valor_actual': inventario.valor_inventario(),
                }
            }
        except ProductoNormal.DoesNotExist:
            return {
                'producto': producto,
                'tipo': 'NORMAL',
                'error': 'No tiene inventario registrado'
            }
    
    @staticmethod
    def rastrear_venta(venta):
        """
        Rastrea todos los quintales/productos usados en una venta
        
        Args:
            venta: Instancia de Venta
        
        Returns:
            dict con información de trazabilidad
        """
        from apps.sales_management.models import DetalleVenta
        
        detalles = DetalleVenta.objects.filter(
            venta=venta
        ).select_related('producto')
        
        trazabilidad_items = []
        
        for detalle in detalles:
            if detalle.es_quintal and detalle.quintal_origen:
                # Trazabilidad de quintal
                quintal = detalle.quintal_origen
                trazabilidad_items.append({
                    'producto': detalle.producto.nombre,
                    'tipo': 'QUINTAL',
                    'quintal_codigo': quintal.codigo_unico,
                    'proveedor': quintal.proveedor.nombre_comercial,
                    'lote': quintal.lote_proveedor,
                    'fecha_recepcion': quintal.fecha_recepcion,
                    'cantidad_vendida': detalle.cantidad,
                    'unidad': detalle.unidad_venta.abreviatura if detalle.unidad_venta else ''
                })
            else:
                # Trazabilidad de producto normal
                trazabilidad_items.append({
                    'producto': detalle.producto.nombre,
                    'tipo': 'NORMAL',
                    'cantidad_vendida': detalle.cantidad,
                })
        
        return {
            'venta': venta,
            'numero_venta': venta.numero_venta,
            'fecha': venta.fecha_venta,
            'cliente': venta.cliente.nombre_completo() if venta.cliente else 'Mostrador',
            'items': trazabilidad_items
        }