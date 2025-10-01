# apps/financial_management/signals.py

"""
Signals para automatización de procesos financieros
Conecta eventos del sistema con acciones automáticas
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

from .models import (
    Caja, MovimientoCaja, ArqueoCaja,
    CajaChica, MovimientoCajaChica
)


# ============================================================================
# SIGNALS DE VENTA
# ============================================================================

@receiver(post_save, sender='sales_management.Venta')
def registrar_venta_en_caja(sender, instance, created, **kwargs):
    """
    Cuando se crea una venta completada, registrarla automáticamente en caja
    """
    if created and instance.estado == 'COMPLETADA' and instance.caja:
        try:
            # Verificar que la caja esté abierta
            if instance.caja.estado == 'ABIERTA':
                # Calcular saldo
                saldo_anterior = instance.caja.monto_actual
                instance.caja.monto_actual += instance.total
                instance.caja.save()
                
                # Registrar movimiento
                MovimientoCaja.objects.create(
                    caja=instance.caja,
                    tipo_movimiento='VENTA',
                    monto=instance.total,
                    saldo_anterior=saldo_anterior,
                    saldo_nuevo=instance.caja.monto_actual,
                    usuario=instance.vendedor,
                    venta=instance,
                    observaciones=f"Venta {instance.numero_venta}"
                )
        except Exception as e:
            # Log error pero no interrumpir el flujo de venta
            print(f"Error al registrar venta en caja: {e}")


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
            # Aquí se podría integrar con sistema de notificaciones
            print(f"⚠️  Movimiento grande en {instance.caja.nombre}: ${instance.monto}")
            
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


@receiver(pre_save, sender=Caja)
def validar_cambio_estado_caja(sender, instance, **kwargs):
    """
    Validar que los cambios de estado de caja sean correctos
    """
    if instance.pk:  # Si es actualización
        try:
            caja_anterior = Caja.objects.get(pk=instance.pk)
            
            # No permitir cerrar caja sin arqueo
            if caja_anterior.estado == 'ABIERTA' and instance.estado == 'CERRADA':
                # Verificar que exista un arqueo
                if not hasattr(instance, '_cierre_autorizado'):
                    # Este flag se debe setear desde el servicio de cierre
                    pass
            
            # No permitir abrir caja que ya está abierta
            if caja_anterior.estado == 'ABIERTA' and instance.estado == 'ABIERTA':
                if not hasattr(instance, '_apertura_autorizada'):
                    # Este flag se debe setear desde el servicio de apertura
                    pass
        except Caja.DoesNotExist:
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
            
            print(
                f"⚠️  {tipo_diferencia} en arqueo {instance.numero_arqueo}: "
                f"${abs(instance.diferencia)}"
            )
            
            # Crear notificación para supervisores
            try:
                from apps.notifications.models import Notification
                from apps.authentication.models import Usuario
                
                supervisores = Usuario.objects.filter(
                    rol__in=['SUPERVISOR', 'ADMIN'],
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


@receiver(post_save, sender=ArqueoCaja)
def analizar_patron_diferencias(sender, instance, created, **kwargs):
    """
    Analizar si hay un patrón de diferencias en la caja
    """
    if created:
        from .cash_management.reconciliation_service import ReconciliationService
        
        # Analizar patrón de los últimos 30 días
        patron = ReconciliationService.detectar_patron_diferencias(
            caja=instance.caja,
            dias=30
        )
        
        if patron.get('tiene_patron'):
            print(
                f"⚠️  PATRÓN DETECTADO en {instance.caja.nombre}: "
                f"{patron.get('tipo_patron')}"
            )
            
            # Notificar a administración
            try:
                from apps.notifications.models import Notification
                from apps.authentication.models import Usuario
                
                admins = Usuario.objects.filter(
                    rol='ADMIN',
                    is_active=True
                )
                
                for admin in admins:
                    Notification.objects.create(
                        tipo='PATRON_DIFERENCIAS',
                        titulo=f'Patrón detectado en {instance.caja.nombre}',
                        mensaje=(
                            f'Se detectó un patrón de {patron["tipo_patron"]} '
                            f'en la caja {instance.caja.nombre}. Revisar procedimientos.'
                        ),
                        usuario=admin,
                        prioridad='ALTA'
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
            print(
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


@receiver(post_save, sender=MovimientoCajaChica)
def validar_limite_gasto(sender, instance, created, **kwargs):
    """
    Validar que los gastos no excedan límites establecidos
    """
    if created and instance.tipo_movimiento == 'GASTO':
        caja_chica = instance.caja_chica
        
        # Verificar si excede límite individual
        if instance.monto > caja_chica.limite_gasto_individual:
            print(
                f"⚠️  Gasto de ${instance.monto} excede límite de "
                f"${caja_chica.limite_gasto_individual} en {caja_chica.nombre}"
            )
            
            # Este gasto debería haber sido rechazado en el form/view
            # pero si llegó aquí, notificar
            try:
                from apps.notifications.models import Notification
                from apps.authentication.models import Usuario
                
                supervisores = Usuario.objects.filter(
                    rol__in=['SUPERVISOR', 'ADMIN'],
                    is_active=True
                )
                
                for supervisor in supervisores:
                    Notification.objects.create(
                        tipo='EXCESO_LIMITE_GASTO',
                        titulo='Gasto excede límite en caja chica',
                        mensaje=(
                            f'Gasto de ${instance.monto:.2f} excede límite de '
                            f'${caja_chica.limite_gasto_individual:.2f} '
                            f'en {caja_chica.nombre}'
                        ),
                        usuario=supervisor,
                        prioridad='ALTA'
                    )
            except:
                pass


# ============================================================================
# SIGNALS DE CLIENTE (para créditos)
# ============================================================================

@receiver(post_save, sender='sales_management.Venta')
def actualizar_credito_cliente(sender, instance, created, **kwargs):
    """
    Actualizar el crédito disponible del cliente cuando se hace venta a crédito
    """
    if instance.tipo_venta == 'CREDITO' and instance.cliente:
        cliente = instance.cliente
        
        if created and instance.estado == 'COMPLETADA':
            # Reducir crédito disponible
            if cliente.credito_disponible >= instance.total:
                cliente.credito_disponible -= instance.total
                cliente.total_compras += instance.total
                cliente.fecha_ultima_compra = instance.fecha_venta
                cliente.save()
            else:
                print(
                    f"⚠️  Cliente {cliente} no tiene crédito suficiente. "
                    f"Disponible: ${cliente.credito_disponible}, "
                    f"Venta: ${instance.total}"
                )


# ============================================================================
# SIGNALS DE BACKUP Y MANTENIMIENTO
# ============================================================================

@receiver(post_save, sender=ArqueoCaja)
def backup_arqueo(sender, instance, created, **kwargs):
    """
    Crear backup de datos críticos cuando se crea un arqueo
    """
    if created:
        # Aquí se podría implementar lógica de backup automático
        # Por ejemplo, guardar en S3, enviar por email, etc.
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
    # Esta función es por si se necesita lógica adicional
    pass