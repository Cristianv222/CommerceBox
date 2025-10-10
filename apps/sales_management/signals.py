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
    """
    Después de guardar un detalle:
    - Recalcular totales de la venta
    """
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