from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import (
    Quintal, MovimientoQuintal, ProductoNormal,
    MovimientoInventario, Producto
)


class InventoryService:
    """
    Servicio central para gestión de inventario
    Maneja operaciones de entrada/salida para quintales y productos normales
    """
    
    @staticmethod
    @transaction.atomic
    def registrar_entrada_quintal(producto, proveedor, peso_inicial, unidad_medida,
                                  costo_total, usuario, **kwargs):
        """
        Registra entrada de un nuevo quintal al inventario
        
        Args:
            producto: Instancia de Producto (tipo QUINTAL)
            proveedor: Instancia de Proveedor
            peso_inicial: Decimal - peso del quintal
            unidad_medida: Instancia de UnidadMedida
            costo_total: Decimal - costo total de compra
            usuario: Usuario que registra
            **kwargs: Campos opcionales (fecha_vencimiento, lote_proveedor, etc)
        
        Returns:
            Quintal: Instancia del quintal creado
        """
        from ..utils.barcode_generator import BarcodeGenerator
        
        # Generar código único
        codigo_unico = kwargs.get('codigo_unico') or BarcodeGenerator.generar_codigo_quintal(producto)
        
        # Crear quintal
        quintal = Quintal.objects.create(
            codigo_unico=codigo_unico,
            producto=producto,
            proveedor=proveedor,
            peso_inicial=peso_inicial,
            peso_actual=peso_inicial,
            unidad_medida=unidad_medida,
            costo_total=costo_total,
            costo_por_unidad=costo_total / peso_inicial,
            fecha_recepcion=kwargs.get('fecha_recepcion', timezone.now()),
            fecha_vencimiento=kwargs.get('fecha_vencimiento'),
            lote_proveedor=kwargs.get('lote_proveedor', ''),
            numero_factura_compra=kwargs.get('numero_factura_compra', ''),
            origen=kwargs.get('origen', ''),
            usuario_registro=usuario,
            estado='DISPONIBLE'
        )
        
        return quintal
    
    @staticmethod
    @transaction.atomic
    def registrar_venta_quintal(quintal, peso_venta, unidad_medida, usuario, 
                                venta=None, observaciones=''):
        """
        Registra salida por venta de un quintal (método FIFO)
        
        Args:
            quintal: Instancia de Quintal
            peso_venta: Decimal - peso vendido
            unidad_medida: Instancia de UnidadMedida
            usuario: Usuario que registra la venta
            venta: Instancia de Venta (opcional)
            observaciones: str
        
        Returns:
            MovimientoQuintal: Movimiento registrado
        
        Raises:
            ValueError: Si no hay suficiente peso disponible
        """
        # Verificar disponibilidad
        if quintal.peso_actual < peso_venta:
            raise ValueError(
                f"No hay suficiente peso disponible. "
                f"Disponible: {quintal.peso_actual}, Solicitado: {peso_venta}"
            )
        
        # Capturar estado antes
        peso_antes = quintal.peso_actual
        
        # Actualizar peso
        quintal.peso_actual -= peso_venta
        quintal.save()
        
        # Registrar movimiento
        movimiento = MovimientoQuintal.objects.create(
            quintal=quintal,
            tipo_movimiento='VENTA',
            peso_movimiento=-peso_venta,
            peso_antes=peso_antes,
            peso_despues=quintal.peso_actual,
            unidad_medida=unidad_medida,
            venta=venta,
            usuario=usuario,
            observaciones=observaciones or f"Venta de {peso_venta} {unidad_medida.abreviatura}"
        )
        
        return movimiento
    
    @staticmethod
    @transaction.atomic
    def registrar_entrada_producto_normal(producto_normal, cantidad, costo_unitario,
                                         usuario, tipo='ENTRADA_COMPRA', **kwargs):
        """
        Registra entrada de inventario para producto normal
        
        Args:
            producto_normal: Instancia de ProductoNormal
            cantidad: int - cantidad de unidades
            costo_unitario: Decimal
            usuario: Usuario que registra
            tipo: str - tipo de movimiento
            **kwargs: compra, observaciones
        
        Returns:
            MovimientoInventario
        """
        stock_antes = producto_normal.stock_actual
        
        # Actualizar stock
        producto_normal.stock_actual += cantidad
        
        # Actualizar costo promedio ponderado
        if stock_antes > 0:
            costo_total_anterior = stock_antes * producto_normal.costo_unitario
            costo_total_nuevo = cantidad * costo_unitario
            stock_total = stock_antes + cantidad
            producto_normal.costo_unitario = (costo_total_anterior + costo_total_nuevo) / stock_total
        else:
            producto_normal.costo_unitario = costo_unitario
        
        producto_normal.fecha_ultima_entrada = timezone.now()
        producto_normal.save()
        
        # Registrar movimiento
        movimiento = MovimientoInventario.objects.create(
            producto_normal=producto_normal,
            tipo_movimiento=tipo,
            cantidad=cantidad,
            stock_antes=stock_antes,
            stock_despues=producto_normal.stock_actual,
            costo_unitario=costo_unitario,
            costo_total=cantidad * costo_unitario,
            compra=kwargs.get('compra'),
            usuario=usuario,
            observaciones=kwargs.get('observaciones', '')
        )
        
        return movimiento
    
    @staticmethod
    @transaction.atomic
    def registrar_salida_producto_normal(producto_normal, cantidad, usuario,
                                        tipo='SALIDA_VENTA', venta=None, observaciones=''):
        """
        Registra salida de inventario para producto normal
        
        Args:
            producto_normal: Instancia de ProductoNormal
            cantidad: int - cantidad de unidades
            usuario: Usuario que registra
            tipo: str - tipo de movimiento
            venta: Instancia de Venta (opcional)
            observaciones: str
        
        Returns:
            MovimientoInventario
        
        Raises:
            ValueError: Si no hay suficiente stock
        """
        # Verificar stock
        if producto_normal.stock_actual < cantidad:
            raise ValueError(
                f"Stock insuficiente. "
                f"Disponible: {producto_normal.stock_actual}, Solicitado: {cantidad}"
            )
        
        stock_antes = producto_normal.stock_actual
        
        # Actualizar stock
        producto_normal.stock_actual -= cantidad
        producto_normal.fecha_ultima_salida = timezone.now()
        producto_normal.save()
        
        # Registrar movimiento
        movimiento = MovimientoInventario.objects.create(
            producto_normal=producto_normal,
            tipo_movimiento=tipo,
            cantidad=-cantidad,
            stock_antes=stock_antes,
            stock_despues=producto_normal.stock_actual,
            costo_unitario=producto_normal.costo_unitario,
            costo_total=cantidad * producto_normal.costo_unitario,
            venta=venta,
            usuario=usuario,
            observaciones=observaciones
        )
        
        return movimiento
    
    @staticmethod
    def verificar_disponibilidad_quintal(producto, peso_solicitado):
        """
        Verifica si hay suficiente peso disponible de un producto a granel
        
        Args:
            producto: Instancia de Producto (tipo QUINTAL)
            peso_solicitado: Decimal
        
        Returns:
            dict: {
                'disponible': bool,
                'peso_total_disponible': Decimal,
                'quintales_disponibles': QuerySet
            }
        """
        quintales = Quintal.objects.filter(
            producto=producto,
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).order_by('fecha_recepcion')  # FIFO
        
        peso_total = sum(q.peso_actual for q in quintales)
        
        return {
            'disponible': peso_total >= peso_solicitado,
            'peso_total_disponible': peso_total,
            'quintales_disponibles': quintales
        }
    
    @staticmethod
    def verificar_disponibilidad_normal(producto, cantidad_solicitada):
        """
        Verifica si hay suficiente stock de un producto normal
        
        Args:
            producto: Instancia de Producto (tipo NORMAL)
            cantidad_solicitada: int
        
        Returns:
            dict: {
                'disponible': bool,
                'stock_actual': int,
                'producto_normal': ProductoNormal
            }
        """
        try:
            producto_normal = producto.inventario_normal
            return {
                'disponible': producto_normal.stock_actual >= cantidad_solicitada,
                'stock_actual': producto_normal.stock_actual,
                'producto_normal': producto_normal
            }
        except ProductoNormal.DoesNotExist:
            return {
                'disponible': False,
                'stock_actual': 0,
                'producto_normal': None
            }