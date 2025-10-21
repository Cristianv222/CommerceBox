# apps/financial_management/signals.py

"""
Signals para automatización de procesos financieros
Conecta eventos del sistema con acciones automáticas
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
import logging

from .models import (
    Caja, MovimientoCaja, ArqueoCaja,
    CajaChica, MovimientoCajaChica
)

logger = logging.getLogger(__name__)


# ============================================================================
# SIGNALS DE VENTA - AUTO-GESTIÓN DE CAJAS
# ============================================================================

@receiver(post_save, sender='sales_management.Venta')
def registrar_venta_en_caja_automatico(sender, instance, created, **kwargs):
    """
    🆕 VERSIÓN MEJORADA CON AUTO-CREACIÓN DE CAJAS
    
    Cuando se completa una venta:
    1. Si no tiene caja asignada, obtiene o crea una automáticamente
    2. Registra el movimiento en la caja
    3. No requiere que la caja esté pre-abierta
    """
    # Solo procesar cuando cambia a COMPLETADA
    if instance.estado != 'COMPLETADA':
        return
    
    # Usar flag temporal para evitar múltiples ejecuciones
    flag_key = f'_venta_en_caja_{instance.id}'
    if hasattr(instance, flag_key):
        return
    setattr(instance, flag_key, True)
    
    # Verificar si ya tiene movimiento de caja para evitar duplicados
    from .models import MovimientoCaja
    from django.db import transaction
    
    with transaction.atomic():
        # Verificar dentro de transacción
        if MovimientoCaja.objects.filter(venta=instance, tipo_movimiento='VENTA').exists():
            logger.debug(f"Venta {instance.numero_venta} ya tiene movimiento - saltando")
            return
        
        try:
            from .cash_management.auto_cash_service import AutoCashService
            
            # Registrar venta en caja (auto-crea si no existe)
            movimiento = AutoCashService.registrar_venta_en_caja(
                venta=instance,
                usuario=instance.vendedor
            )
            
            logger.info(
                f"✅ Venta {instance.numero_venta} registrada en caja "
                f"{movimiento.caja.nombre}"
            )
            
        except Exception as e:
            # Log error pero no interrumpir el flujo de venta
            logger.error(
                f"❌ Error al registrar venta {instance.numero_venta} en caja: {e}",
                exc_info=True
            )


@receiver(post_save, sender='sales_management.Pago')
def actualizar_monto_venta(sender, instance, created, **kwargs):
    """
    Cuando se registra un pago, actualizar el monto pagado de la venta
    """
    if created:
        venta = instance.venta
        
        # Recalcular total pagado
        from django.db.models import Sum
        total_pagado = venta.pagos.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')
        
        venta.monto_pagado = total_pagado
        
        # Si está completamente pagada, cambiar estado
        if venta.monto_pagado >= venta.total and venta.estado == 'PENDIENTE':
            venta.estado = 'COMPLETADA'
        
        venta.save()


# ============================================================================
# SIGNALS DE CAJA
# ============================================================================

@receiver(post_save, sender=MovimientoCaja)
def notificar_movimiento_grande(sender, instance, created, **kwargs):
    """
    Notificar cuando hay un movimiento grande en caja
    """
    if created:
        # Definir umbral para movimientos "grandes"
        UMBRAL_GRANDE = Decimal('500.00')
        
        if instance.monto >= UMBRAL_GRANDE:
            logger.warning(
                f"⚠️  Movimiento grande en {instance.caja.nombre}: ${instance.monto}"
            )
            
            # Opcional: Crear notificación en base de datos
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    tipo='MOVIMIENTO_GRANDE',
                    titulo=f'Movimiento de ${instance.monto} en {instance.caja.nombre}',
                    mensaje=f'{instance.get_tipo_movimiento_display()}: {instance.observaciones}',
                    usuario=instance.usuario
                )
            except:
                pass


# ============================================================================
# SIGNALS DE ARQUEO
# ============================================================================

@receiver(post_save, sender=ArqueoCaja)
def notificar_diferencia_arqueo(sender, instance, created, **kwargs):
    """
    Notificar cuando hay diferencias significativas en arqueos
    """
    if created:
        # Umbral de diferencia significativa
        UMBRAL_DIFERENCIA = Decimal('5.00')
        
        if abs(instance.diferencia) >= UMBRAL_DIFERENCIA:
            # Notificar diferencia
            tipo_diferencia = (
                'SOBRANTE' if instance.diferencia > 0 else 'FALTANTE'
            )
            
            logger.warning(
                f"⚠️  {tipo_diferencia} en arqueo {instance.numero_arqueo}: "
                f"${abs(instance.diferencia)}"
            )
            
            # Crear notificación para supervisores
            try:
                from apps.notifications.models import Notification
                from apps.authentication.models import Usuario
                
                supervisores = Usuario.objects.filter(
                    rol__nombre__in=['Supervisor', 'Administrador'],
                    is_active=True
                )
                
                for supervisor in supervisores:
                    Notification.objects.create(
                        tipo='DIFERENCIA_ARQUEO',
                        titulo=f'{tipo_diferencia} en arqueo',
                        mensaje=(
                            f'Arqueo {instance.numero_arqueo} de {instance.caja.nombre} '
                            f'tiene {tipo_diferencia.lower()} de ${abs(instance.diferencia):.2f}'
                        ),
                        usuario=supervisor,
                        prioridad='ALTA' if abs(instance.diferencia) >= Decimal('20.00') else 'MEDIA'
                    )
            except:
                pass


# ============================================================================
# SIGNALS DE CAJA CHICA
# ============================================================================

@receiver(post_save, sender=MovimientoCajaChica)
def verificar_reposicion_caja_chica(sender, instance, created, **kwargs):
    """
    Verificar si la caja chica necesita reposición después de un gasto
    """
    if created and instance.tipo_movimiento == 'GASTO':
        caja_chica = instance.caja_chica
        
        if caja_chica.necesita_reposicion():
            logger.warning(
                f"⚠️  Caja chica '{caja_chica.nombre}' necesita reposición de "
                f"${caja_chica.monto_a_reponer()}"
            )
            
            # Notificar al responsable
            try:
                from apps.notifications.models import Notification
                
                Notification.objects.create(
                    tipo='REPOSICION_CAJA_CHICA',
                    titulo=f'Reposición necesaria en {caja_chica.nombre}',
                    mensaje=(
                        f'La caja chica {caja_chica.nombre} necesita reposición de '
                        f'${caja_chica.monto_a_reponer():.2f}. '
                        f'Saldo actual: ${caja_chica.monto_actual:.2f}'
                    ),
                    usuario=caja_chica.responsable,
                    prioridad='MEDIA'
                )
            except:
                pass


# ============================================================================
# UTILIDADES
# ============================================================================

def conectar_signals():
    """
    Función para asegurar que todos los signals estén conectados
    Se llama desde apps.py
    """
    # Los signals se conectan automáticamente con el decorador @receiver
    logger.info("✅ Signals de financial_management conectados")
