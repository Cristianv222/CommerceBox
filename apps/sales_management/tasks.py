# apps/sales_management/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Venta, Cliente


@shared_task
def generar_reporte_diario():
    """
    Genera reporte diario de ventas automáticamente
    Se ejecuta todos los días a las 23:59
    """
    hoy = timezone.now().date()
    
    ventas = Venta.objects.filter(
        fecha_venta__date=hoy,
        estado='COMPLETADA'
    )
    
    total_ventas = ventas.count()
    monto_total = sum(v.total for v in ventas) if ventas else Decimal('0')
    
    # Aquí puedes enviar el reporte por email o guardarlo
    print(f"Reporte del día {hoy}: {total_ventas} ventas - Total: ${monto_total}")
    
    return {
        'fecha': str(hoy),
        'total_ventas': total_ventas,
        'monto_total': float(monto_total)
    }


@shared_task
def verificar_creditos_vencidos():
    """
    Verifica créditos vencidos y envía notificaciones
    Se ejecuta diariamente
    """
    hoy = timezone.now().date()
    
    ventas_vencidas = Venta.objects.filter(
        tipo_venta='CREDITO',
        estado='COMPLETADA',
        fecha_vencimiento__lt=hoy,
        monto_pagado__lt=F('total')
    )
    
    for venta in ventas_vencidas:
        # Aquí enviar notificación al cliente
        print(f"Crédito vencido: {venta.numero_venta} - Cliente: {venta.cliente}")
    
    return {
        'creditos_vencidos': ventas_vencidas.count()
    }


@shared_task
def actualizar_estadisticas_clientes():
    """
    Actualiza estadísticas de clientes
    Se ejecuta semanalmente
    """
    clientes = Cliente.objects.filter(activo=True)
    
    for cliente in clientes:
        total_compras = Venta.objects.filter(
            cliente=cliente,
            estado='COMPLETADA'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        cliente.total_compras = total_compras
        cliente.save()
    
    return {
        'clientes_actualizados': clientes.count()
    }