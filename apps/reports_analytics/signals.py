# apps/reports_analytics/signals.py

"""
Señales del módulo Reports & Analytics
Automatización de tareas basadas en eventos del sistema
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from apps.authentication.models import Usuario
from apps.sales_management.models import Venta
from apps.inventory_management.models import Quintal, ProductoNormal
from .models import ConfiguracionReporte, SnapshotDashboard


# ============================================================================
# SEÑALES DE CONFIGURACIÓN
# ============================================================================

@receiver(post_save, sender=Usuario)
def crear_configuracion_predeterminada(sender, instance, created, **kwargs):
    """
    Crea configuración de reportes predeterminada para nuevos usuarios
    """
    if created and instance.rol in ['ADMIN', 'SUPERVISOR', 'VENDEDOR']:
        # Configuración de Dashboard
        ConfiguracionReporte.objects.get_or_create(
            usuario=instance,
            tipo_reporte='DASHBOARD',
            defaults={
                'nombre_configuracion': 'Dashboard Predeterminado',
                'configuracion': {
                    'mostrar_ventas_dia': True,
                    'mostrar_ventas_mes': True,
                    'mostrar_inventario': True,
                    'mostrar_alertas': True,
                    'mostrar_top_productos': True,
                    'limite_top_productos': 10,
                    'actualizar_automatico': True,
                    'intervalo_actualizacion': 60  # segundos
                },
                'es_predeterminada': True
            }
        )
        
        # Configuración de Reportes de Ventas
        ConfiguracionReporte.objects.get_or_create(
            usuario=instance,
            tipo_reporte='VENTAS',
            defaults={
                'nombre_configuracion': 'Ventas Predeterminado',
                'configuracion': {
                    'periodo_predeterminado': 'MES',
                    'mostrar_graficos': True,
                    'incluir_rentabilidad': True,
                    'agrupar_por': 'dia'
                },
                'es_predeterminada': True
            }
        )


# ============================================================================
# SEÑALES DE SNAPSHOTS AUTOMÁTICOS
# ============================================================================

@receiver(post_save, sender=Venta)
def actualizar_snapshot_en_venta(sender, instance, created, **kwargs):
    """
    Actualiza snapshot cuando se completa una venta
    Solo en horario de trabajo para evitar sobrecarga
    """
    if instance.estado == 'COMPLETADA':
        hora_actual = timezone.now().hour
        
        # Solo actualizar en horario de trabajo (8am - 8pm)
        if 8 <= hora_actual <= 20:
            # Verificar si ya existe snapshot de hoy
            hoy = timezone.now().date()
            ultimo_snapshot = SnapshotDashboard.objects.filter(
                fecha_snapshot__date=hoy,
                tipo='DIARIO'
            ).order_by('-fecha_snapshot').first()
            
            # Solo crear snapshot si pasaron al menos 5 minutos del último
            if not ultimo_snapshot or (
                timezone.now() - ultimo_snapshot.fecha_snapshot
            ) > timedelta(minutes=5):
                crear_snapshot_dashboard('DIARIO')


# ============================================================================
# SEÑALES DE ALERTAS AUTOMÁTICAS
# ============================================================================

@receiver(post_save, sender=Quintal)
def verificar_quintal_critico(sender, instance, created, **kwargs):
    """
    Verifica si un quintal llega a nivel crítico
    """
    if not created and instance.esta_critico():
        # Aquí se podría enviar notificación
        # Por ahora solo registramos el evento
        pass


@receiver(post_save, sender=ProductoNormal)
def verificar_stock_critico(sender, instance, created, **kwargs):
    """
    Verifica si un producto llega a stock mínimo
    """
    if not created and instance.necesita_reorden():
        # Aquí se podría enviar notificación
        pass


# ============================================================================
# LIMPIEZA AUTOMÁTICA DE SNAPSHOTS ANTIGUOS
# ============================================================================

@receiver(post_save, sender=SnapshotDashboard)
def limpiar_snapshots_antiguos(sender, instance, created, **kwargs):
    """
    Limpia snapshots antiguos para no ocupar mucho espacio en BD
    Mantiene:
    - Todos los snapshots de los últimos 7 días
    - 1 snapshot diario de los últimos 90 días
    - 1 snapshot mensual para histórico
    """
    if created:
        fecha_limite_detalle = timezone.now() - timedelta(days=7)
        fecha_limite_diario = timezone.now() - timedelta(days=90)
        
        # Eliminar snapshots de minuto/hora antiguos (más de 7 días)
        SnapshotDashboard.objects.filter(
            tipo__in=['MINUTO', 'HORARIO'],
            fecha_snapshot__lt=fecha_limite_detalle
        ).delete()
        
        # Eliminar snapshots diarios antiguos (más de 90 días)
        # Pero mantener el primero de cada mes
        snapshots_diarios_antiguos = SnapshotDashboard.objects.filter(
            tipo='DIARIO',
            fecha_snapshot__lt=fecha_limite_diario
        ).exclude(
            fecha_snapshot__day=1  # Mantener primer día de cada mes
        )
        
        snapshots_diarios_antiguos.delete()


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def crear_snapshot_dashboard(tipo='DIARIO'):
    """
    Crea un snapshot del dashboard actual
    
    Args:
        tipo: Tipo de snapshot (MINUTO, HORARIO, DIARIO, MENSUAL)
    """
    try:
        from .generators import DashboardDataGenerator
        
        generator = DashboardDataGenerator()
        dashboard_data = generator.generar_dashboard_completo()
        
        # Extraer métricas principales
        ventas = dashboard_data.get('ventas', {})
        inventario = dashboard_data.get('inventario', {})
        financiero = dashboard_data.get('financiero', {})
        
        # Crear snapshot
        SnapshotDashboard.objects.create(
            fecha_snapshot=timezone.now(),
            tipo=tipo,
            total_ventas_dia=ventas.get('total_dia', 0),
            total_ventas_mes=ventas.get('total_mes', 0),
            numero_ventas_dia=ventas.get('cantidad_dia', 0),
            numero_ventas_mes=ventas.get('cantidad_mes', 0),
            valor_inventario_total=inventario.get('valor_total', 0),
            productos_criticos=inventario.get('criticos', 0),
            productos_agotados=inventario.get('agotados', 0),
            efectivo_en_caja=financiero.get('efectivo_caja', 0),
            metricas_completas=dashboard_data
        )
        
        return True
    except Exception as e:
        # Log del error (usar logging en producción)
        print(f"Error al crear snapshot: {str(e)}")
        return False


def notificar_alerta_critica(tipo_alerta, mensaje, datos=None):
    """
    Sistema de notificación de alertas críticas
    
    Args:
        tipo_alerta: Tipo de alerta (STOCK, VENCIMIENTO, CAJA, etc)
        mensaje: Mensaje de la alerta
        datos: Datos adicionales de contexto
    """
    # TODO: Implementar sistema de notificaciones
    # - Email
    # - Notificaciones push
    # - SMS
    # - Slack/Telegram
    pass


def generar_reporte_programado(tipo_reporte, configuracion):
    """
    Genera reportes de forma programada (para usar con Celery)
    
    Args:
        tipo_reporte: Tipo de reporte a generar
        configuracion: Configuración del reporte
    """
    # TODO: Implementar con Celery para ejecución asíncrona
    pass


# ============================================================================
# SEÑALES DE DEBUG (SOLO DESARROLLO)
# ============================================================================

# Descomentar solo en desarrollo para debugging
# import logging
# logger = logging.getLogger(__name__)

# @receiver(post_save, sender=ConfiguracionReporte)
# def log_configuracion_cambios(sender, instance, created, **kwargs):
#     """Log de cambios en configuraciones"""
#     if created:
#         logger.info(f"Nueva configuración creada: {instance.nombre_configuracion}")
#     else:
#         logger.info(f"Configuración actualizada: {instance.nombre_configuracion}")

# @receiver(post_save, sender=SnapshotDashboard)
# def log_snapshot_creado(sender, instance, created, **kwargs):
#     """Log de creación de snapshots"""
#     if created:
#         logger.info(f"Snapshot creado: {instance.tipo} - {instance.fecha_snapshot}")