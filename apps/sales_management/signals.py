# apps/sales_management/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Sum  # ✅ Agregar esta importación
from decimal import Decimal

from .models import Venta, DetalleVenta, Pago


@receiver(pre_save, sender=DetalleVenta)
def detalle_venta_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar un detalle de venta:
    - Calcular totales automáticamente
    """
    instance.calcular_totales()


@receiver(post_save, sender=DetalleVenta)
def detalle_venta_post_save(sender, instance, created, **kwargs):
    print(f"DEBUG Signal ejecutado: created={created}, producto={instance.producto.nombre if instance.producto else 'None'}")
    print(f"  tipo_inventario={instance.producto.tipo_inventario if instance.producto else 'None'}")
    print(f"  quintal={instance.quintal}")
    print(f"  peso_vendido={instance.peso_vendido}")
    """
    Después de guardar un detalle:
    - Descontar del inventario (si es nuevo)
    - Recalcular totales de la venta
    """
    from django.db import transaction
    
    if created:  # Solo al crear un nuevo detalle
        # Descontar del inventario
        with transaction.atomic():
            producto = instance.producto
            
            if producto.tipo_inventario == 'QUINTAL' and instance.quintal:
                # Descontar peso del quintal
                quintal = instance.quintal
                quintal.peso_actual -= instance.peso_vendido
                if quintal.peso_actual <= 0:
                    quintal.peso_actual = 0
                    quintal.estado = 'AGOTADO'
                quintal.save()
                print(f"✅ Quintal {quintal.codigo_unico} actualizado: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}")
                
            elif producto.tipo_inventario == 'NORMAL' and instance.cantidad_unidades:
                # Descontar unidades del inventario normal
                try:
                    inventario = producto.inventario_normal
                    if inventario:
                        inventario.stock_actual -= instance.cantidad_unidades
                        if inventario.stock_actual < 0:
                            inventario.stock_actual = 0
                        inventario.save()
                        print(f"✅ Stock de {producto.nombre} actualizado: {inventario.stock_actual}")
                except Exception as e:
                    print(f"Error al actualizar inventario: {e}")
    
    # Siempre recalcular totales de la venta
    instance.venta.calcular_totales()


@receiver(post_save, sender=Pago)
def pago_post_save(sender, instance, created, **kwargs):
    """
    Después de registrar un pago:
    - Actualizar monto pagado en la venta
    - Actualizar estado si está completamente pagada
    """
    venta = instance.venta
    
    # Calcular total pagado
    venta.monto_pagado = venta.pagos.aggregate(
        total=Sum('monto')  # ✅ Cambiar sum() por Sum()
    )['total'] or Decimal('0')
    
    # Calcular cambio si aplica
    if venta.monto_pagado > venta.total:
        venta.cambio = venta.monto_pagado - venta.total
        venta.monto_pagado = venta.total
    
    venta.save()