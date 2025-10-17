# apps/notifications/signals.py

"""
Señales del Sistema de Notificaciones
Escucha eventos de otros módulos y genera notificaciones automáticamente
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal

# Importar modelos de otros módulos
from apps.inventory_management.models import (
    Quintal, MovimientoQuintal, ProductoNormal, 
    MovimientoInventario
)
from apps.sales_management.models import (
    Venta, DetalleVenta, Devolucion
)
from apps.stock_alert_system.models import (
    AlertaStock, EstadoStock
)

# Importar servicio de notificaciones
from .services.notification_service import NotificationService


# ============================================================================
# SEÑALES DE INVENTARIO - QUINTALES
# ============================================================================

@receiver(post_save, sender=MovimientoQuintal)
def notificar_movimiento_quintal(sender, instance, created, **kwargs):
    """
    Después de un movimiento de quintal:
    - Verificar si el quintal está crítico
    - Generar notificación si es necesario
    """
    if not created:
        return
    
    # Solo notificar para ciertos tipos de movimientos
    if instance.tipo_movimiento not in ['VENTA', 'MERMA', 'AJUSTE_NEGATIVO']:
        return
    
    quintal = instance.quintal
    porcentaje = quintal.porcentaje_restante()
    
    # Quintal crítico (menos del 10%)
    if 0 < porcentaje <= 10:
        NotificationService.crear_notificacion_stock_critico_quintal(
            quintal=quintal,
            porcentaje_restante=porcentaje
        )
    
    # Quintal agotado
    elif porcentaje == 0:
        NotificationService.crear_notificacion_quintal_agotado(
            quintal=quintal
        )


@receiver(post_save, sender=Quintal)
def notificar_quintal_proximo_vencer(sender, instance, created, **kwargs):
    """
    Al crear o actualizar un quintal:
    - Verificar si está próximo a vencer
    """
    if not instance.fecha_vencimiento:
        return
    
    from datetime import timedelta
    from django.utils import timezone
    
    # Convertir fecha_vencimiento a date si es string
    fecha_venc = instance.fecha_vencimiento
    if isinstance(fecha_venc, str):
        from datetime import datetime
        fecha_venc = datetime.strptime(fecha_venc, '%Y-%m-%d').date()
    elif not isinstance(fecha_venc, date):
        return  # Si no es ni string ni date, salir
    
    dias_para_vencer = (fecha_venc - timezone.now().date()).days
    
    # Notificar si vence en 7 días o menos
    if 0 <= dias_para_vencer <= 7 and instance.estado == 'DISPONIBLE':
        NotificationService.crear_notificacion_vencimiento_proximo(
            quintal=instance,
            dias_restantes=dias_para_vencer
        )


# ============================================================================
# SEÑALES DE INVENTARIO - PRODUCTOS NORMALES
# ============================================================================

@receiver(post_save, sender=MovimientoInventario)
def notificar_movimiento_inventario(sender, instance, created, **kwargs):
    """
    Después de un movimiento de inventario:
    - Verificar stock actual
    - Generar notificación si está crítico o bajo
    """
    if not created:
        return
    
    # Solo notificar para salidas (ventas, mermas, ajustes negativos)
    if instance.tipo_movimiento not in ['SALIDA_VENTA', 'SALIDA_MERMA', 'SALIDA_AJUSTE']:
        return
    
    producto_normal = instance.producto_normal
    estado_stock = producto_normal.estado_stock()
    
    # Stock crítico
    if estado_stock == 'CRITICO':
        NotificationService.crear_notificacion_stock_critico(
            producto_normal=producto_normal
        )
    
    # Stock bajo
    elif estado_stock == 'BAJO':
        NotificationService.crear_notificacion_stock_bajo(
            producto_normal=producto_normal
        )
    
    # Stock agotado
    elif estado_stock == 'AGOTADO':
        NotificationService.crear_notificacion_stock_agotado(
            producto_normal=producto_normal
        )


# ============================================================================
# SEÑALES DE VENTAS
# ============================================================================

@receiver(post_save, sender=Venta)
def notificar_venta_importante(sender, instance, created, **kwargs):
    """
    Al crear o actualizar una venta:
    - Notificar ventas grandes
    - Notificar si requiere autorización
    """
    from .models import ConfiguracionNotificacion
    
    config = ConfiguracionNotificacion.get_config()
    
    # Solo para ventas completadas o pendientes
    if instance.estado not in ['COMPLETADA', 'PENDIENTE']:
        return
    
    # Venta grande (supera el monto configurado)
    if config.notif_venta_grande and instance.total >= config.notif_venta_grande_monto:
        NotificationService.crear_notificacion_venta_grande(
            venta=instance
        )


@receiver(post_save, sender=DetalleVenta)
def notificar_descuento_excesivo(sender, instance, created, **kwargs):
    """
    Al crear un detalle de venta:
    - Verificar si el descuento es excesivo
    """
    from .models import ConfiguracionNotificacion
    
    config = ConfiguracionNotificacion.get_config()
    
    if not config.notif_descuento_excesivo:
        return
    
    # Verificar descuento
    if instance.descuento_porcentaje >= config.notif_descuento_excesivo_porcentaje:
        NotificationService.crear_notificacion_descuento_excesivo(
            detalle_venta=instance
        )


@receiver(post_save, sender=Devolucion)
def notificar_devolucion(sender, instance, created, **kwargs):
    """
    Al crear una devolución:
    - Notificar a supervisores
    """
    if not created:
        return
    
    from .models import ConfiguracionNotificacion
    
    config = ConfiguracionNotificacion.get_config()
    
    if config.notif_devolucion:
        NotificationService.crear_notificacion_devolucion(
            devolucion=instance
        )


# ============================================================================
# SEÑALES DE ALERTAS DE STOCK
# ============================================================================

@receiver(post_save, sender=AlertaStock)
def notificar_alerta_critica(sender, instance, created, **kwargs):
    """
    Al crear una alerta de stock:
    - Generar notificación si es crítica
    """
    if not created:
        return
    
    # Solo para alertas críticas o de prioridad alta
    if instance.prioridad not in ['ALTA', 'CRITICA']:
        return
    
    NotificationService.crear_notificacion_desde_alerta(
        alerta=instance
    )


@receiver(post_save, sender=EstadoStock)
def notificar_cambio_estado_stock(sender, instance, **kwargs):
    """
    Al cambiar el estado de stock:
    - Notificar si cambia a CRITICO o AGOTADO
    """
    # Verificar si cambió el estado del semáforo
    if not instance.pk:
        return
    
    try:
        estado_anterior = EstadoStock.objects.get(pk=instance.pk)
    except EstadoStock.DoesNotExist:
        return
    
    # Si cambió a estado crítico o agotado
    if instance.estado_semaforo != estado_anterior.estado_semaforo:
        if instance.estado_semaforo in ['CRITICO', 'AGOTADO']:
            NotificationService.crear_notificacion_cambio_estado_stock(
                estado_stock=instance,
                estado_anterior=estado_anterior.estado_semaforo
            )


# ============================================================================
# SEÑALES FINANCIERAS (Para integración futura)
# ============================================================================

# Estas señales se activarán cuando se implementen los modelos financieros

# @receiver(post_save, sender='financial_management.CajaChica')
# def notificar_caja_chica_baja(sender, instance, **kwargs):
#     """
#     Al actualizar caja chica:
#     - Notificar si el saldo está bajo
#     """
#     from .models import ConfiguracionNotificacion
#     
#     config = ConfiguracionNotificacion.get_config()
#     
#     if not config.notif_caja_chica_baja:
#         return
#     
#     if instance.saldo_actual <= config.notif_caja_chica_limite:
#         NotificationService.crear_notificacion_caja_chica_baja(
#             caja_chica=instance
#         )


# @receiver(post_save, sender='financial_management.ArqueoCaja')
# def notificar_diferencia_arqueo(sender, instance, created, **kwargs):
#     """
#     Al crear un arqueo de caja:
#     - Notificar si hay diferencias significativas
#     """
#     from .models import ConfiguracionNotificacion
#     
#     config = ConfiguracionNotificacion.get_config()
#     
#     if not config.notif_diferencia_arqueo:
#         return
#     
#     diferencia = abs(instance.diferencia)
#     
#     if diferencia >= config.notif_diferencia_arqueo_monto:
#         NotificationService.crear_notificacion_diferencia_arqueo(
#             arqueo=instance,
#             diferencia=diferencia
#         )


# ============================================================================
# SEÑALES DE USUARIO (Para notificaciones de sistema)
# ============================================================================

from apps.authentication.models import Usuario

@receiver(post_save, sender=Usuario)
def crear_preferencias_notificacion(sender, instance, created, **kwargs):
    """
    Al crear un usuario:
    - Crear preferencias de notificación por defecto
    """
    if created:
        from .models import PreferenciasNotificacion
        
        PreferenciasNotificacion.objects.get_or_create(
            usuario=instance,
            defaults={
                'recibir_notificaciones_web': True,
                'recibir_notificaciones_email': True,
                'notif_stock': True,
                'notif_ventas': True,
                'notif_financiero': True,
                'notif_sistema': True,
            }
        )


# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def notificar_error_sistema(mensaje, detalles=''):
    """
    Función helper para notificar errores del sistema
    """
    NotificationService.crear_notificacion_error_sistema(
        mensaje=mensaje,
        detalles=detalles
    )