# apps/sales_management/pos/pos_service.py

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class POSService:
    """Servicio para operaciones del punto de venta"""
    
    @staticmethod
    @transaction.atomic
    def crear_venta(vendedor, cliente=None, tipo_venta='CONTADO', descuento=Decimal('0'), 
                   observaciones='', caja=None):
        """
        Crea una nueva venta en estado PENDIENTE
        
        Args:
            vendedor: Usuario que realiza la venta
            cliente: Cliente (opcional para ventas al público)
            tipo_venta: CONTADO o CREDITO
            descuento: Descuento general a nivel de venta
            observaciones: Observaciones de la venta
            caja: Caja asociada a la venta
            
        Returns:
            Venta: Nueva venta creada
        """
        from ..models import Venta
        
        # Validaciones
        if tipo_venta == 'CREDITO' and not cliente:
            raise ValidationError("Las ventas a crédito requieren un cliente")
        
        venta = Venta.objects.create(
            vendedor=vendedor,
            cliente=cliente,
            tipo_venta=tipo_venta,
            estado='PENDIENTE',
            descuento=descuento,
            observaciones=observaciones,
            caja=caja
        )
        
        # Generar número de venta automáticamente
        venta.save()
        
        logger.info(f"✅ Venta creada: {venta.numero_venta} - Vendedor: {vendedor.username}")
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def agregar_item_normal(venta, producto, cantidad_unidades, precio_unitario, 
                           descuento_porcentaje=Decimal('0')):
        """
        Agrega un producto normal a la venta
        
        Args:
            venta: Venta a la que se agrega el item
            producto: Producto a agregar (tipo NORMAL)
            cantidad_unidades: Cantidad a vender
            precio_unitario: Precio por unidad
            descuento_porcentaje: Descuento en porcentaje para este item
            
        Returns:
            DetalleVenta: Detalle creado
        """
        from ..models import DetalleVenta
        from apps.inventory_management.models import ProductoNormal
        
        # Validaciones
        if venta.estado != 'PENDIENTE':
            raise ValidationError('Solo se pueden agregar items a ventas pendientes')
        
        if not producto.es_normal():
            raise ValidationError('El producto no es tipo NORMAL')
        
        # Verificar stock disponible
        try:
            inventario = producto.inventario_normal
            if inventario.stock_actual < cantidad_unidades:
                raise ValidationError(
                    f'Stock insuficiente para {producto.nombre}. '
                    f'Disponible: {inventario.stock_actual} unidades'
                )
        except ProductoNormal.DoesNotExist:
            raise ValidationError('Producto sin inventario configurado')
        
        # Calcular montos
        subtotal = Decimal(str(cantidad_unidades)) * Decimal(str(precio_unitario))
        descuento_monto = subtotal * (Decimal(str(descuento_porcentaje)) / 100)
        total = subtotal - descuento_monto
        
        # Costo para rentabilidad
        costo_unitario = inventario.costo_unitario or Decimal('0')
        costo_total = Decimal(str(cantidad_unidades)) * costo_unitario
        
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
        
        # Descontar stock temporalmente (se confirmará al finalizar)
        inventario.stock_actual -= cantidad_unidades
        inventario.save()
        
        # Recalcular totales de la venta
        venta.calcular_totales()
        
        logger.info(f"📦 Item agregado a {venta.numero_venta}: {producto.nombre} x{cantidad_unidades}")
        
        return detalle
    
    @staticmethod
    @transaction.atomic
    def agregar_item_quintal(venta, producto, quintal, peso_vendido, precio_por_unidad, 
                            descuento_porcentaje=Decimal('0')):
        """
        Agrega un item de quintal a la venta
        
        Args:
            venta: Venta a la que se agrega el item
            producto: Producto a agregar (tipo QUINTAL)
            quintal: Quintal específico del que se vende
            peso_vendido: Peso que se vende
            precio_por_unidad: Precio por unidad de peso
            descuento_porcentaje: Descuento en porcentaje para este item
            
        Returns:
            DetalleVenta: Detalle creado
        """
        from ..models import DetalleVenta
        
        # Validaciones
        if venta.estado != 'PENDIENTE':
            raise ValidationError('Solo se pueden agregar items a ventas pendientes')
        
        if not producto.es_quintal():
            raise ValidationError('El producto no es tipo QUINTAL')
        
        if quintal.estado != 'DISPONIBLE':
            raise ValidationError('El quintal no está disponible para venta')
        
        # Verificar peso disponible
        if quintal.peso_actual < peso_vendido:
            raise ValidationError(
                f'Peso insuficiente en quintal {quintal.codigo_quintal}. '
                f'Disponible: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}'
            )
        
        # Calcular montos
        subtotal = Decimal(str(peso_vendido)) * Decimal(str(precio_por_unidad))
        descuento_monto = subtotal * (Decimal(str(descuento_porcentaje)) / 100)
        total = subtotal - descuento_monto
        
        # Costo para rentabilidad
        costo_unitario = quintal.costo_por_unidad or Decimal('0')
        costo_total = Decimal(str(peso_vendido)) * costo_unitario
        
        # Crear detalle
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            quintal=quintal,
            peso_vendido=peso_vendido,
            precio_unitario=precio_por_unidad,
            unidad_medida=quintal.unidad_medida,
            descuento_porcentaje=descuento_porcentaje,
            descuento_monto=descuento_monto,
            subtotal=subtotal,
            total=total,
            costo_unitario=costo_unitario,
            costo_total=costo_total,
            orden=venta.detalles.count() + 1
        )
        
        # Descontar peso temporalmente (se confirmará al finalizar)
        quintal.peso_actual -= peso_vendido
        if quintal.peso_actual <= 0:
            quintal.peso_actual = Decimal('0')
            quintal.estado = 'AGOTADO'
        quintal.save()
        
        # Recalcular totales de la venta
        venta.calcular_totales()
        
        logger.info(
            f"⚖️ Item agregado a {venta.numero_venta}: "
            f"{producto.nombre} - {peso_vendido} {quintal.unidad_medida.abreviatura}"
        )
        
        return detalle
    
    @staticmethod
    @transaction.atomic
    def eliminar_item(detalle):
        """
        Elimina un item de la venta (solo si está en estado PENDIENTE)
        
        Args:
            detalle: DetalleVenta a eliminar
        """
        venta = detalle.venta
        
        if venta.estado != 'PENDIENTE':
            raise ValidationError('Solo se pueden eliminar items de ventas pendientes')
        
        # Revertir stock/peso antes de eliminar
        producto = detalle.producto
        
        if producto.es_quintal() and detalle.quintal:
            quintal = detalle.quintal
            quintal.peso_actual += detalle.peso_vendido
            if quintal.estado == 'AGOTADO' and quintal.peso_actual > 0:
                quintal.estado = 'DISPONIBLE'
            quintal.save()
            
        elif producto.es_normal() and detalle.cantidad_unidades:
            try:
                inventario = producto.inventario_normal
                inventario.stock_actual += detalle.cantidad_unidades
                inventario.save()
            except Exception as e:
                logger.error(f"Error al revertir stock: {e}")
        
        # Eliminar el detalle
        detalle.delete()
        
        # Recalcular totales
        venta.calcular_totales()
        
        logger.info(f"🗑️ Item eliminado de {venta.numero_venta}")
    
    @staticmethod
    @transaction.atomic
    def procesar_pago(venta, forma_pago, monto, usuario, referencia='', caja=None):
        """
        Procesa un pago de la venta
        """
        from ..models import Pago
        
        print("=" * 80)
        print(f"🔥 PROCESAR_PAGO LLAMADO")
        print(f"   Venta: {venta.numero_venta}")
        print(f"   Forma Pago: {forma_pago}")
        print(f"   Monto: {monto}")
        print("=" * 80)
        
        # Validaciones
        if venta.estado == 'ANULADA':
            raise ValidationError('No se pueden registrar pagos en ventas anuladas')
        
        if monto <= 0:
            raise ValidationError('El monto del pago debe ser mayor a cero')
        
        # Validar que no se pague de más
        saldo = venta.saldo_pendiente()
        if monto > saldo:
            raise ValidationError(
                f'El monto del pago (${monto}) excede el saldo pendiente (${saldo})'
            )
        
        print("✅ Validaciones pasadas, creando objeto Pago...")
        
        # Crear pago
        pago = Pago.objects.create(
            venta=venta,
            forma_pago=forma_pago,
            monto=monto,
            usuario=usuario,
            referencia=referencia,
            caja=caja,
            fecha_pago=timezone.now()
        )
        
        print(f"✅ Pago creado con ID: {pago.id}")
        print(f"   Ahora debería ejecutarse el signal pago_post_save...")
        
        # Actualizar monto pagado de la venta
        venta.monto_pagado += monto
        
        # Calcular cambio si es efectivo y excede el total
        if forma_pago == 'EFECTIVO' and venta.monto_pagado > venta.total:
            venta.cambio = venta.monto_pagado - venta.total
        
        # ✅ DETERMINAR ESTADO DE PAGO SEGÚN TIPO DE VENTA
        print(f"🔍 Evaluando estado_pago en pos_service...")
        print(f"   tipo_venta: {venta.tipo_venta}")
        print(f"   monto_pagado: {venta.monto_pagado}")
        print(f"   total: {venta.total}")
        
        if venta.tipo_venta == 'CONTADO':
            # Ventas al contado siempre quedan como PAGADAS
            if venta.monto_pagado >= venta.total:
                venta.estado_pago = 'PAGADO'
                print(f"✅ POS Service: Venta al CONTADO marcada como PAGADA")
            else:
                venta.estado_pago = 'PENDIENTE'
                print(f"⏳ POS Service: Venta al CONTADO - Pago parcial")
        
        elif venta.tipo_venta == 'CREDITO':
            # Ventas a crédito quedan pendientes hasta liquidar la deuda
            if venta.monto_pagado >= venta.total:
                venta.estado_pago = 'PAGADO'
                print(f"✅ POS Service: Venta a CRÉDITO liquidada")
            else:
                venta.estado_pago = 'PENDIENTE'
                print(f"⏳ POS Service: Venta a CRÉDITO pendiente")
        
        else:
            # Por defecto, verificar si está completamente pagado
            venta.estado_pago = 'PAGADO' if venta.monto_pagado >= venta.total else 'PENDIENTE'
        
        print(f"💾 Guardando venta con estado_pago: {venta.estado_pago}")
        venta.save()
        
        print(f"✅ PROCESAR_PAGO COMPLETADO")
        print("=" * 80)
        print()
        
        return pago
    
    @staticmethod
    @transaction.atomic
    def finalizar_venta(venta):
        """
        Finaliza una venta y actualiza el estado
        🖨️ AHORA TAMBIÉN IMPRIME AUTOMÁTICAMENTE EL TICKET
        
        Args:
            venta: Venta a finalizar
            
        Returns:
            Venta: Venta finalizada
        """
        from apps.inventory_management.models import MovimientoQuintal, MovimientoInventario
        
        # Validaciones
        if venta.estado == 'COMPLETADA':
            raise ValidationError('Esta venta ya está finalizada')
        
        if venta.estado == 'ANULADA':
            raise ValidationError('No se puede finalizar una venta anulada')
        
        if not venta.detalles.exists():
            raise ValidationError('La venta no tiene items')
        
        # Validar que esté pagada (para ventas al contado)
        if venta.tipo_venta == 'CONTADO' and not venta.esta_pagada():
            raise ValidationError(
                'Las ventas al contado deben estar completamente pagadas para finalizarlas'
            )
        
        # Validar crédito disponible del cliente si es a crédito
        if venta.tipo_venta == 'CREDITO' and venta.cliente:
            if venta.total > venta.cliente.credito_disponible:
                raise ValidationError(
                    f'El monto de la venta (${venta.total}) excede el crédito '
                    f'disponible del cliente (${venta.cliente.credito_disponible})'
                )
        
        # Registrar movimientos de inventario
        for detalle in venta.detalles.all():
            producto = detalle.producto
            
            if producto.es_quintal() and detalle.quintal:
                # Registrar movimiento de quintal
                quintal = detalle.quintal
                quintal.fecha_ultima_salida = timezone.now()
                quintal.save()
                
                MovimientoQuintal.objects.create(
                    quintal=quintal,
                    tipo_movimiento='SALIDA_VENTA',
                    peso_movimiento=-detalle.peso_vendido,
                    peso_antes=quintal.peso_actual + detalle.peso_vendido,
                    peso_despues=quintal.peso_actual,
                    unidad_medida=quintal.unidad_medida,
                    costo_por_unidad=detalle.costo_unitario,
                    costo_total=detalle.costo_total,
                    venta=venta,
                    usuario=venta.vendedor,
                    observaciones=f"Venta {venta.numero_venta}"
                )
                
            elif producto.es_normal() and detalle.cantidad_unidades:
                # Registrar movimiento de inventario
                try:
                    inventario = producto.inventario_normal
                    inventario.fecha_ultima_salida = timezone.now()
                    inventario.save()
                    
                    MovimientoInventario.objects.create(
                        producto_normal=inventario,
                        tipo_movimiento='SALIDA_VENTA',
                        cantidad=-detalle.cantidad_unidades,
                        stock_antes=inventario.stock_actual + detalle.cantidad_unidades,
                        stock_despues=inventario.stock_actual,
                        costo_unitario=detalle.costo_unitario,
                        costo_total=detalle.costo_total,
                        venta=venta,
                        usuario=venta.vendedor,
                        observaciones=f"Venta {venta.numero_venta}"
                    )
                except Exception as e:
                    logger.error(f"Error al registrar movimiento de inventario: {e}")
        
        # Actualizar estado
        venta.estado = 'COMPLETADA'
        venta.fecha_venta = timezone.now()
        venta.save()
        
        # Actualizar estadísticas del cliente si existe
        if venta.cliente:
            cliente = venta.cliente
            cliente.fecha_ultima_compra = timezone.now()
            cliente.total_compras += venta.total
            
            # Si es venta a crédito, descontar del crédito disponible
            if venta.tipo_venta == 'CREDITO':
                cliente.credito_disponible -= venta.total
            
            cliente.save()
            
            logger.info(f"👤 Cliente actualizado: {cliente.nombre}")
        
        logger.info(f"✅ Venta finalizada: {venta.numero_venta} - Total: ${venta.total}")
        
        # NOTA: El registro en caja se hace automáticamente vía signal
        # No es necesario registrarlo aquí para evitar duplicados
        
        # 🖨️ IMPRIMIR TICKET AUTOMÁTICAMENTE
        try:
            from apps.hardware_integration.models import Impresora
            from apps.hardware_integration.printers.ticket_printer import TicketPrinter
            from apps.hardware_integration.api.agente_views import crear_trabajo_impresion
            
            # Obtener la impresora principal activa
            impresora = Impresora.objects.filter(
                activa=True,
                tipo_impresora__in=['TERMICA_FACTURA', 'TERMICA_TICKET']
            ).first()
            
            if impresora:
                logger.info(f"🖨️ Imprimiendo ticket para venta {venta.numero_venta}")
                
                # Generar comandos ESC/POS del ticket
                comandos_hex = TicketPrinter.generar_comandos_ticket(venta, impresora)
                
                # Encolar trabajo de impresión
                trabajo_id = crear_trabajo_impresion(
                    usuario=venta.vendedor,
                    impresora_nombre=impresora.nombre_driver or impresora.nombre,
                    comandos_hex=comandos_hex,
                    tipo='ticket',
                    prioridad=2  # Alta prioridad para tickets de venta
                )
                
                logger.info(f"✅ Ticket encolado exitosamente con ID: {trabajo_id}")
                
            else:
                logger.warning("⚠️ No hay impresora activa configurada. Ticket no impreso.")
                
        except ImportError:
            logger.warning("⚠️ Módulo de impresión no disponible. Ticket no impreso.")
        except Exception as e:
            # No fallar la venta si hay error de impresión
            logger.error(f"❌ Error al imprimir ticket: {e}", exc_info=True)
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def anular_venta(venta, motivo='', usuario=None):
        """
        Anula una venta y revierte el stock/peso
        
        Solo se pueden anular ventas que:
        1. No estén ya anuladas
        2. Se anulen el mismo día (opcional, según política)
        
        Args:
            venta: Venta a anular
            motivo: Motivo de la anulación
            usuario: Usuario que anula (opcional)
            
        Returns:
            Venta: Venta anulada
        """
        from apps.inventory_management.models import MovimientoQuintal, MovimientoInventario
        
        # Validaciones
        if venta.estado == 'ANULADA':
            raise ValidationError('Esta venta ya está anulada')
        
        # Validación opcional: solo permitir anular el mismo día
        # if venta.fecha_venta and venta.fecha_venta.date() != timezone.now().date():
        #     raise ValidationError('Solo se pueden anular ventas del mismo día')
        
        # Revertir stock/peso de cada detalle
        for detalle in venta.detalles.all():
            producto = detalle.producto
            
            if producto.es_quintal() and detalle.quintal:
                # Revertir peso al quintal
                quintal = detalle.quintal
                peso_antes = quintal.peso_actual
                quintal.peso_actual += detalle.peso_vendido
                
                if quintal.estado == 'AGOTADO' and quintal.peso_actual > 0:
                    quintal.estado = 'DISPONIBLE'
                
                quintal.save()
                
                # Registrar movimiento de anulación
                if venta.estado == 'COMPLETADA':
                    MovimientoQuintal.objects.create(
                        quintal=quintal,
                        tipo_movimiento='AJUSTE_POSITIVO',
                        peso_movimiento=detalle.peso_vendido,
                        peso_antes=peso_antes,
                        peso_despues=quintal.peso_actual,
                        unidad_medida=quintal.unidad_medida,
                        usuario=usuario or venta.vendedor,
                        observaciones=f"Anulación de venta {venta.numero_venta}. Motivo: {motivo}"
                    )
                
            elif producto.es_normal() and detalle.cantidad_unidades:
                # Revertir unidades al inventario
                try:
                    inventario = producto.inventario_normal
                    stock_antes = inventario.stock_actual
                    inventario.stock_actual += detalle.cantidad_unidades
                    inventario.save()
                    
                    # Registrar movimiento de anulación
                    if venta.estado == 'COMPLETADA':
                        MovimientoInventario.objects.create(
                            producto_normal=inventario,
                            tipo_movimiento='ENTRADA_AJUSTE',
                            cantidad=detalle.cantidad_unidades,
                            stock_antes=stock_antes,
                            stock_despues=inventario.stock_actual,
                            costo_unitario=detalle.costo_unitario,
                            costo_total=detalle.costo_total,
                            usuario=usuario or venta.vendedor,
                            observaciones=f"Anulación de venta {venta.numero_venta}. Motivo: {motivo}"
                        )
                except Exception as e:
                    logger.error(f"Error al revertir inventario: {e}")
        
        # Revertir estadísticas del cliente
        if venta.cliente and venta.estado == 'COMPLETADA':
            cliente = venta.cliente
            cliente.total_compras -= venta.total
            
            if venta.tipo_venta == 'CREDITO':
                cliente.credito_disponible += venta.total
            
            cliente.save()
        
        # Actualizar estado de la venta
        venta.estado = 'ANULADA'
        usuario_str = usuario.username if usuario else 'Sistema'
        venta.observaciones = f"ANULADA por {usuario_str} el {timezone.now()}\nMotivo: {motivo}"
        venta.save()
        
        logger.warning(f"⚠️ Venta anulada: {venta.numero_venta} - Motivo: {motivo}")
        
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
        from apps.inventory_management.models import MovimientoQuintal, MovimientoInventario
        
        if devolucion.estado != 'APROBADA':
            raise ValidationError("Solo se pueden procesar devoluciones aprobadas")
        
        detalle = devolucion.detalle_venta
        producto = detalle.producto
        
        if producto.es_quintal() and detalle.quintal:
            # Devolver peso al quintal original
            quintal = detalle.quintal
            peso_antes = quintal.peso_actual
            quintal.peso_actual += devolucion.cantidad_devuelta
            
            if quintal.estado == 'AGOTADO' and quintal.peso_actual > 0:
                quintal.estado = 'DISPONIBLE'
            
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
            
        elif producto.es_normal():
            # Devolver unidades al inventario
            try:
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
            except Exception as e:
                logger.error(f"Error al procesar devolución: {e}")
                raise ValidationError(f"Error al procesar devolución: {str(e)}")
        
        logger.info(f"🔄 Devolución procesada: {devolucion.numero_devolucion}")
        
        return devolucion