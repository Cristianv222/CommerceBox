# apps/sales_management/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
import logging

from .models import Venta, DetalleVenta, Pago

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=DetalleVenta)
def detalle_venta_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar un detalle de venta:
    - Calcular totales automáticamente
    """
    instance.calcular_totales()


@receiver(post_save, sender=DetalleVenta)
def detalle_venta_post_save(sender, instance, created, **kwargs):
    """
    Después de guardar un detalle:
    - Descontar del inventario (si es nuevo)
    - Recalcular totales de la venta
    """
    logger.debug(
        f"Signal ejecutado: created={created}, "
        f"producto={instance.producto.nombre if instance.producto else 'None'}"
    )
    logger.debug(
        f"  tipo_inventario={instance.producto.tipo_inventario if instance.producto else 'None'}"
    )
    logger.debug(f"  quintal={instance.quintal}")
    logger.debug(f"  peso_vendido={instance.peso_vendido}")
    
    if created:  # Solo al crear un nuevo detalle
        producto = instance.producto
        
        if producto.tipo_inventario == 'QUINTAL' and instance.quintal:
            # Descontar peso del quintal
            quintal = instance.quintal
            print(f"🔍 Quintal ANTES: {quintal.peso_actual}")
            
            quintal.peso_actual -= instance.peso_vendido
            if quintal.peso_actual <= 0:
                quintal.peso_actual = 0
                quintal.estado = 'AGOTADO'
            
            quintal.save()
            print(
                f"✅ Quintal {quintal.codigo_quintal} actualizado: "
                f"{quintal.peso_actual} {quintal.unidad_medida.abreviatura}"
            )
            
        elif producto.tipo_inventario == 'NORMAL' and instance.cantidad_unidades:
            # Descontar unidades del inventario normal
            try:
                inventario = producto.inventario_normal
                if inventario:
                    print(
                        f"🔍 Stock ANTES: {inventario.stock_actual}, "
                        f"Descontar: {instance.cantidad_unidades}"
                    )
                    
                    inventario.stock_actual -= instance.cantidad_unidades
                    if inventario.stock_actual < 0:
                        inventario.stock_actual = 0
                    
                    inventario.save()
                    print(f"✅ Stock de {producto.nombre} actualizado: {inventario.stock_actual}")
                    
            except Exception as e:
                logger.error(f"❌ Error al actualizar inventario: {e}", exc_info=True)
    
    # Siempre recalcular totales de la venta
    instance.venta.calcular_totales()


@receiver(post_save, sender=Pago)
def pago_post_save(sender, instance, created, **kwargs):
    """
    Después de registrar un pago:
    - Actualizar monto pagado en la venta
    - Actualizar estado_pago según tipo de venta
    """
    print("=" * 80)
    print("🔥 SIGNAL pago_post_save EJECUTADO")
    print("=" * 80)
    
    venta = instance.venta
    
    print(f"📊 Venta: {venta.numero_venta}")
    print(f"📊 Tipo Venta: {venta.tipo_venta}")
    print(f"📊 Total: {venta.total}")
    
    # Calcular total pagado
    venta.monto_pagado = venta.pagos.aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0')
    
    print(f"📊 Monto Pagado: {venta.monto_pagado}")
    
    # Calcular cambio si aplica
    if venta.monto_pagado > venta.total:
        venta.cambio = venta.monto_pagado - venta.total
        venta.monto_pagado = venta.total
        print(f"💵 Cambio calculado: {venta.cambio}")
    
    # ✅ DETERMINAR ESTADO DE PAGO SEGÚN TIPO DE VENTA
    print("🔍 EVALUANDO ESTADO DE PAGO...")
    
    if venta.tipo_venta == 'CONTADO':
        print("✅ ES VENTA AL CONTADO")
        # Ventas al contado quedan como PAGADAS cuando se paga el total
        if venta.monto_pagado >= venta.total:
            venta.estado_pago = 'PAGADO'
            print("✅✅✅ MARCANDO COMO PAGADO ✅✅✅")
        else:
            venta.estado_pago = 'PENDIENTE'
            print("⏳ MARCANDO COMO PENDIENTE (pago parcial)")
    
    elif venta.tipo_venta == 'CREDITO':
        print("💳 ES VENTA A CRÉDITO")
        # Ventas a crédito quedan pendientes hasta liquidar completamente
        if venta.monto_pagado >= venta.total:
            venta.estado_pago = 'PAGADO'
            print("✅ MARCANDO COMO PAGADO (liquidada completamente)")
        else:
            venta.estado_pago = 'PENDIENTE'
            saldo_pendiente = venta.total - venta.monto_pagado
            print(f"⏳ MARCANDO COMO PENDIENTE - Saldo: ${saldo_pendiente:.2f}")
    
    else:
        print(f"⚠️ TIPO DE VENTA DESCONOCIDO: {venta.tipo_venta}")
        # Por defecto, verificar si está completamente pagado
        venta.estado_pago = 'PAGADO' if venta.monto_pagado >= venta.total else 'PENDIENTE'
        print(f"❓ Estado asignado: {venta.estado_pago}")
    
    print(f"💾 GUARDANDO venta con estado_pago={venta.estado_pago}")
    venta.save()
    print("✅ VENTA GUARDADA")
    print("=" * 80)
    print()