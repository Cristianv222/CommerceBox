# apps/sales_management/pos/pos_service.py

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from apps.sales_management.models import Venta, DetalleVenta, Pago, Cliente, Devolucion
from apps.inventory_management.models import (
    Producto, Quintal, MovimientoQuintal, 
    ProductoNormal, MovimientoInventario
)


class POSService:
    """
    Servicio principal para el punto de venta
    Maneja la lógica de ventas unificada para quintales y productos normales
    """
    
    @staticmethod
    def generar_numero_venta():
        """Genera el siguiente número de venta correlativo"""
        ultima_venta = Venta.objects.order_by('-numero_venta').first()
        
        if ultima_venta and ultima_venta.numero_venta.startswith('VNT-'):
            try:
                ultimo_numero = int(ultima_venta.numero_venta.split('-')[-1])
                siguiente = ultimo_numero + 1
            except:
                siguiente = 1
        else:
            siguiente = 1
        
        año_actual = timezone.now().year
        return f"VNT-{año_actual}-{siguiente:05d}"
    
    @staticmethod
    def generar_numero_devolucion():
        """Genera el siguiente número de devolución correlativo"""
        ultima_devolucion = Devolucion.objects.order_by('-numero_devolucion').first()
        
        if ultima_devolucion and ultima_devolucion.numero_devolucion.startswith('DEV-'):
            try:
                ultimo_numero = int(ultima_devolucion.numero_devolucion.split('-')[-1])
                siguiente = ultimo_numero + 1
            except:
                siguiente = 1
        else:
            siguiente = 1
        
        año_actual = timezone.now().year
        return f"DEV-{año_actual}-{siguiente:05d}"
    
    @staticmethod
    @transaction.atomic
    def crear_venta(vendedor, cliente=None, tipo_venta='CONTADO', 
                   fecha_vencimiento=None, descuento_general=Decimal('0'), 
                   observaciones='', caja=None):
        """
        Crea una nueva venta en estado PENDIENTE
        
        Args:
            vendedor: Usuario que realiza la venta
            cliente: Cliente (opcional para ventas al público)
            tipo_venta: CONTADO o CREDITO
            fecha_vencimiento: Fecha de vencimiento si es crédito
            descuento_general: Descuento a nivel de venta
            observaciones: Observaciones de la venta
            caja: Caja asociada
        
        Returns:
            Venta: Nueva venta creada
        """
        # Validaciones
        if tipo_venta == 'CREDITO' and not cliente:
            raise ValueError("Las ventas a crédito requieren un cliente")
        
        if tipo_venta == 'CREDITO' and not fecha_vencimiento:
            # Calcular fecha de vencimiento basada en días de crédito del cliente
            dias_credito = cliente.dias_credito if cliente else 30
            fecha_vencimiento = timezone.now().date() + timedelta(days=dias_credito)
        
        venta = Venta.objects.create(
            numero_venta=POSService.generar_numero_venta(),
            vendedor=vendedor,
            cliente=cliente,
            tipo_venta=tipo_venta,
            fecha_vencimiento=fecha_vencimiento,
            descuento=descuento_general,
            observaciones=observaciones,
            caja=caja,
            estado='PENDIENTE'
        )
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def agregar_item_quintal(venta, producto, quintal, peso_vendido, 
                            precio_por_unidad, descuento_porcentaje=Decimal('0')):
        """
        Agrega un item de quintal a la venta
        
        Args:
            venta: Venta a la que se agrega el item
            producto: Producto (tipo QUINTAL)
            quintal: Quintal específico del que se vende
            peso_vendido: Peso que se vende
            precio_por_unidad: Precio por unidad de peso
            descuento_porcentaje: Descuento en porcentaje
        
        Returns:
            DetalleVenta: Detalle creado
        """
        # Validaciones
        if not producto.es_quintal():
            raise ValueError("El producto no es tipo quintal")
        
        if quintal.peso_actual < peso_vendido:
            raise ValueError(
                f"No hay suficiente peso en el quintal. "
                f"Disponible: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}"
            )
        
        if quintal.estado != 'DISPONIBLE':
            raise ValueError("El quintal no está disponible para venta")
        
        # Calcular montos
        subtotal = peso_vendido * precio_por_unidad
        descuento_monto = subtotal * (descuento_porcentaje / 100)
        total = subtotal - descuento_monto
        
        # Costo para cálculo de rentabilidad
        costo_unitario = quintal.costo_por_unidad
        costo_total = peso_vendido * costo_unitario
        
        # Crear detalle
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            quintal=quintal,
            peso_vendido=peso_vendido,
            unidad_medida=quintal.unidad_medida,
            precio_por_unidad_peso=precio_por_unidad,
            descuento_porcentaje=descuento_porcentaje,
            descuento_monto=descuento_monto,
            subtotal=subtotal,
            total=total,
            costo_unitario=costo_unitario,
            costo_total=costo_total,
            orden=venta.detalles.count() + 1
        )
        
        # Recalcular totales de la venta
        venta.calcular_totales()
        
        return detalle
    
    @staticmethod
    @transaction.atomic
    def agregar_item_normal(venta, producto, cantidad_unidades, 
                           precio_unitario, descuento_porcentaje=Decimal('0')):
        """
        Agrega un item de producto normal a la venta
        
        Args:
            venta: Venta a la que se agrega el item
            producto: Producto (tipo NORMAL)
            cantidad_unidades: Cantidad a vender
            precio_unitario: Precio por unidad
            descuento_porcentaje: Descuento en porcentaje
        
        Returns:
            DetalleVenta: Detalle creado
        """
        # Validaciones
        if not producto.es_normal():
            raise ValueError("El producto no es tipo normal")
        
        try:
            inventario = producto.inventario_normal
        except ProductoNormal.DoesNotExist:
            raise ValueError("El producto no tiene inventario configurado")
        
        if inventario.stock_actual < cantidad_unidades:
            raise ValueError(
                f"No hay suficiente stock. "
                f"Disponible: {inventario.stock_actual} unidades"
            )
        
        # Calcular montos
        subtotal = cantidad_unidades * precio_unitario
        descuento_monto = subtotal * (descuento_porcentaje / 100)
        total = subtotal - descuento_monto
        
        # Costo para rentabilidad
        costo_unitario = inventario.costo_unitario
        costo_total = cantidad_unidades * costo_unitario
        
        # Crear detalle
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad_unidades=cantidad_unidades,
            precio_unitario=precio_unitario,
            descuento_porcentaje=descuento_porcentaje,
            descuento_monto=descuento_monto,
            subtotal=subtotal,
            total=total,
            costo_unitario=costo_unitario,
            costo_total=costo_total,
            orden=venta.detalles.count() + 1
        )
        
        # Recalcular totales de la venta
        venta.calcular_totales()
        
        return detalle
    
    @staticmethod
    @transaction.atomic
    def procesar_pago(venta, forma_pago, monto, usuario, 
                     numero_referencia='', banco=''):
        """
        Registra un pago para la venta
        
        Args:
            venta: Venta a la que se aplica el pago
            forma_pago: Forma de pago (EFECTIVO, TARJETA, etc)
            monto: Monto del pago
            usuario: Usuario que procesa el pago
            numero_referencia: Número de referencia del pago
            banco: Banco (si aplica)
        
        Returns:
            Pago: Pago registrado
        """
        if monto <= 0:
            raise ValueError("El monto del pago debe ser mayor a cero")
        
        saldo_pendiente = venta.saldo_pendiente()
        if monto > saldo_pendiente:
            raise ValueError(
                f"El monto (${monto}) excede el saldo pendiente (${saldo_pendiente})"
            )
        
        pago = Pago.objects.create(
            venta=venta,
            forma_pago=forma_pago,
            monto=monto,
            numero_referencia=numero_referencia,
            banco=banco,
            usuario=usuario
        )
        
        return pago
    
    @staticmethod
    @transaction.atomic
    def finalizar_venta(venta):
        """
        Finaliza la venta y actualiza el inventario
        
        1. Valida que la venta esté completamente pagada
        2. Descuenta del inventario (quintales y productos normales)
        3. Registra movimientos de inventario
        4. Actualiza estado de la venta a COMPLETADA
        5. Actualiza estadísticas del cliente
        
        Args:
            venta: Venta a finalizar
        
        Returns:
            Venta: Venta finalizada
        """
        # Validación de pago
        if not venta.esta_pagada():
            raise ValueError(
                f"La venta no está completamente pagada. "
                f"Falta: ${venta.saldo_pendiente()}"
            )
        
        # Procesar cada detalle
        for detalle in venta.detalles.all():
            producto = detalle.producto
            
            if producto.es_quintal():
                # Descontar peso del quintal
                quintal = detalle.quintal
                peso_antes = quintal.peso_actual
                quintal.peso_actual -= detalle.peso_vendido
                
                if quintal.peso_actual < 0:
                    raise ValueError(
                        f"Error en quintal {quintal.codigo_unico}: "
                        f"peso negativo después de la venta"
                    )
                
                quintal.save()
                
                # Registrar movimiento del quintal
                MovimientoQuintal.objects.create(
                    quintal=quintal,
                    tipo_movimiento='VENTA',
                    peso_movimiento=-detalle.peso_vendido,
                    peso_antes=peso_antes,
                    peso_despues=quintal.peso_actual,
                    unidad_medida=quintal.unidad_medida,
                    venta=venta,
                    usuario=venta.vendedor,
                    observaciones=f"Venta {venta.numero_venta}"
                )
            
            else:
                # Descontar unidades del inventario
                inventario = producto.inventario_normal
                stock_antes = inventario.stock_actual
                inventario.stock_actual -= detalle.cantidad_unidades
                
                if inventario.stock_actual < 0:
                    raise ValueError(
                        f"Error en producto {producto.nombre}: "
                        f"stock negativo después de la venta"
                    )
                
                inventario.fecha_ultima_salida = timezone.now()
                inventario.save()
                
                # Registrar movimiento de inventario
                MovimientoInventario.objects.create(
                    producto_normal=inventario,
                    tipo_movimiento='SALIDA_VENTA',
                    cantidad=-detalle.cantidad_unidades,
                    stock_antes=stock_antes,
                    stock_despues=inventario.stock_actual,
                    costo_unitario=detalle.costo_unitario,
                    costo_total=detalle.costo_total,
                    venta=venta,
                    usuario=venta.vendedor,
                    observaciones=f"Venta {venta.numero_venta}"
                )
        
        # Actualizar estado de la venta
        venta.estado = 'COMPLETADA'
        venta.save()
        
        # Actualizar estadísticas del cliente
        if venta.cliente:
            cliente = venta.cliente
            cliente.fecha_ultima_compra = timezone.now()
            cliente.total_compras += venta.total
            
            # Si es venta a crédito, descontar del crédito disponible
            if venta.tipo_venta == 'CREDITO':
                cliente.credito_disponible -= venta.total
            
            cliente.save()
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def anular_venta(venta, usuario):
        """
        Anula una venta y revierte el inventario
        
        Solo se pueden anular ventas que:
        1. Estén en estado COMPLETADA
        2. No tengan pagos registrados
        3. Se anulen el mismo día
        
        Args:
            venta: Venta a anular
            usuario: Usuario que anula
        
        Returns:
            Venta: Venta anulada
        """
        # Validaciones
        if venta.estado == 'ANULADA':
            raise ValueError("La venta ya está anulada")
        
        if venta.monto_pagado > 0:
            raise ValueError(
                "No se puede anular una venta con pagos registrados. "
                "Debe procesar una devolución."
            )
        
        # Solo permitir anular el mismo día
        if venta.fecha_venta.date() != timezone.now().date():
            raise ValueError(
                "Solo se pueden anular ventas del mismo día. "
                "Para ventas anteriores, procese una devolución."
            )
        
        # Revertir inventario solo si está completada
        if venta.estado == 'COMPLETADA':
            for detalle in venta.detalles.all():
                producto = detalle.producto
                
                if producto.es_quintal():
                    # Devolver peso al quintal
                    quintal = detalle.quintal
                    peso_antes = quintal.peso_actual
                    quintal.peso_actual += detalle.peso_vendido
                    quintal.save()
                    
                    # Registrar movimiento
                    MovimientoQuintal.objects.create(
                        quintal=quintal,
                        tipo_movimiento='AJUSTE_POSITIVO',
                        peso_movimiento=detalle.peso_vendido,
                        peso_antes=peso_antes,
                        peso_despues=quintal.peso_actual,
                        unidad_medida=quintal.unidad_medida,
                        usuario=usuario,
                        observaciones=f"Anulación de venta {venta.numero_venta}"
                    )
                
                else:
                    # Devolver unidades al inventario
                    inventario = producto.inventario_normal
                    stock_antes = inventario.stock_actual
                    inventario.stock_actual += detalle.cantidad_unidades
                    inventario.save()
                    
                    # Registrar movimiento
                    MovimientoInventario.objects.create(
                        producto_normal=inventario,
                        tipo_movimiento='ENTRADA_AJUSTE',
                        cantidad=detalle.cantidad_unidades,
                        stock_antes=stock_antes,
                        stock_despues=inventario.stock_actual,
                        costo_unitario=detalle.costo_unitario,
                        costo_total=detalle.costo_total,
                        usuario=usuario,
                        observaciones=f"Anulación de venta {venta.numero_venta}"
                    )
        
        # Actualizar estado
        venta.estado = 'ANULADA'
        venta.observaciones += f"\n\nANULADA por {usuario.username} el {timezone.now()}"
        venta.save()
        
        # Revertir estadísticas del cliente
        if venta.cliente:
            cliente = venta.cliente
            cliente.total_compras -= venta.total
            if venta.tipo_venta == 'CREDITO':
                cliente.credito_disponible += venta.total
            cliente.save()
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def procesar_devolucion(devolucion, usuario):
        """
        Procesa una devolución aprobada
        
        1. Devuelve el producto al inventario
        2. Registra movimiento de inventario
        3. Genera nota de crédito (si aplica)
        
        Args:
            devolucion: Devolución aprobada
            usuario: Usuario que procesa
        
        Returns:
            Devolucion: Devolución procesada
        """
        if devolucion.estado != 'APROBADA':
            raise ValueError("Solo se pueden procesar devoluciones aprobadas")
        
        detalle = devolucion.detalle_venta
        producto = detalle.producto
        
        if producto.es_quintal():
            # Devolver peso al quintal original
            quintal = detalle.quintal
            peso_antes = quintal.peso_actual
            quintal.peso_actual += devolucion.cantidad_devuelta
            quintal.save()
            
            # Registrar movimiento
            MovimientoQuintal.objects.create(
                quintal=quintal,
                tipo_movimiento='DEVOLUCION',
                peso_movimiento=devolucion.cantidad_devuelta,
                peso_antes=peso_antes,
                peso_despues=quintal.peso_actual,
                unidad_medida=quintal.unidad_medida,
                usuario=usuario,
                observaciones=f"Devolución {devolucion.numero_devolucion}"
            )
        
        else:
            # Devolver unidades al inventario
            inventario = producto.inventario_normal
            stock_antes = inventario.stock_actual
            inventario.stock_actual += int(devolucion.cantidad_devuelta)
            inventario.fecha_ultima_entrada = timezone.now()
            inventario.save()
            
            # Registrar movimiento
            MovimientoInventario.objects.create(
                producto_normal=inventario,
                tipo_movimiento='ENTRADA_DEVOLUCION',
                cantidad=int(devolucion.cantidad_devuelta),
                stock_antes=stock_antes,
                stock_despues=inventario.stock_actual,
                costo_unitario=detalle.costo_unitario,
                costo_total=detalle.costo_unitario * int(devolucion.cantidad_devuelta),
                usuario=usuario,
                observaciones=f"Devolución {devolucion.numero_devolucion}"
            )
        
        return devolucion