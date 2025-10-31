# apps/reports_analytics/signals.py

"""
Señales del módulo Reports & Analytics
Automatización de tareas basadas en eventos del sistema
"""

import logging
from decimal import Decimal
from uuid import UUID
from datetime import datetime, date
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from apps.authentication.models import Usuario
from apps.sales_management.models import Venta
from apps.inventory_management.models import Quintal, ProductoNormal
from .models import ConfiguracionReporte, SnapshotDashboard

# Configurar logger
logger = logging.getLogger(__name__)


# ============================================================================
# UTILIDADES PARA SERIALIZACIÓN JSON
# ============================================================================

def convertir_a_json_serializable(obj):
    """
    Convierte recursivamente objetos no-serializables a tipos compatibles con JSON
    
    Maneja:
    - Decimal → float
    - UUID → str
    - datetime/date → str (ISO format)
    - dict/list/tuple → conversión recursiva
    
    Args:
        obj: Objeto a convertir
        
    Returns:
        Objeto completamente serializable a JSON
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convertir_a_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convertir_a_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convertir_a_json_serializable(item) for item in obj)
    elif isinstance(obj, set):
        return [convertir_a_json_serializable(item) for item in obj]
    return obj


# ============================================================================
# SEÑALES DE CONFIGURACIÓN
# ============================================================================

@receiver(post_save, sender=Usuario)
def crear_configuracion_predeterminada(sender, instance, created, **kwargs):
    """
    Crea configuración de reportes predeterminada para nuevos usuarios
    """
    if created and instance.rol in ['ADMIN', 'SUPERVISOR', 'VENDEDOR']:
        try:
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
            
            logger.info(f"✅ Configuraciones predeterminadas creadas para usuario: {instance.username}")
            
        except Exception as e:
            logger.error(f"❌ Error al crear configuraciones predeterminadas: {str(e)}")


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
            try:
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
                    # Ejecutar en una transacción independiente para evitar conflictos
                    transaction.on_commit(lambda: crear_snapshot_dashboard('DIARIO'))
                    
            except Exception as e:
                logger.error(f"❌ Error en actualizar_snapshot_en_venta: {str(e)}")


# ============================================================================
# SEÑALES DE ALERTAS AUTOMÁTICAS
# ============================================================================

@receiver(post_save, sender=Quintal)
def verificar_quintal_critico(sender, instance, created, **kwargs):
    """
    Verifica si un quintal llega a nivel crítico
    """
    try:
        if not created and instance.esta_critico():
            # Obtener el nombre del quintal de forma segura
            nombre_quintal = getattr(instance, 'codigo', None) or getattr(instance, 'nombre', f'ID: {instance.id}')
            
            # Obtener pesos de forma segura
            peso_actual = getattr(instance, 'peso_actual', 0)
            peso_original = getattr(instance, 'peso_original', 0)
            
            logger.warning(
                f"⚠️ Quintal crítico detectado: {nombre_quintal} - "
                f"Peso: {peso_actual}kg"
            )
            
            # Aquí se podría enviar notificación
            notificar_alerta_critica(
                tipo_alerta='QUINTAL_CRITICO',
                mensaje=f'Quintal {nombre_quintal} en nivel crítico',
                datos={
                    'quintal_id': str(instance.id),
                    'codigo': nombre_quintal,
                    'peso_actual': float(peso_actual),
                    'peso_original': float(peso_original)
                }
            )
    except Exception as e:
        logger.error(f"❌ Error en verificar_quintal_critico: {str(e)}", exc_info=True)


@receiver(post_save, sender=ProductoNormal)
def verificar_stock_critico(sender, instance, created, **kwargs):
    """
    Verifica si un producto llega a stock mínimo
    """
    try:
        if not created and hasattr(instance, 'necesita_reorden') and instance.necesita_reorden():
            # Obtener el nombre del producto de forma segura
            # Intenta diferentes atributos comunes
            nombre_producto = (
                getattr(instance, 'nombre', None) or 
                getattr(instance, 'nombre_producto', None) or
                getattr(instance, 'descripcion', None) or
                getattr(instance, 'producto', None) or
                f'Producto ID: {instance.id}'
            )
            
            # Obtener stock actual de forma segura (intenta múltiples nombres posibles)
            stock_actual = (
                getattr(instance, 'stock', None) or
                getattr(instance, 'cantidad_stock', None) or
                getattr(instance, 'stock_actual', None) or
                getattr(instance, 'cantidad', None) or
                0
            )
            
            # Obtener stock mínimo de forma segura
            stock_minimo = (
                getattr(instance, 'stock_minimo', None) or
                getattr(instance, 'punto_reorden', None) or
                getattr(instance, 'minimo', None) or
                0
            )
            
            logger.warning(
                f"⚠️ Stock crítico detectado: {nombre_producto} - "
                f"Stock: {stock_actual}"
            )
            
            # Aquí se podría enviar notificación
            notificar_alerta_critica(
                tipo_alerta='STOCK_CRITICO',
                mensaje=f'Producto {nombre_producto} necesita reorden',
                datos={
                    'producto_id': str(instance.id),
                    'nombre': str(nombre_producto),
                    'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo
                }
            )
    except Exception as e:
        logger.error(f"❌ Error en verificar_stock_critico: {str(e)}", exc_info=True)


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
        try:
            fecha_limite_detalle = timezone.now() - timedelta(days=7)
            fecha_limite_diario = timezone.now() - timedelta(days=90)
            
            # Eliminar snapshots de minuto/hora antiguos (más de 7 días)
            snapshots_eliminados_detalle = SnapshotDashboard.objects.filter(
                tipo__in=['MINUTO', 'HORARIO'],
                fecha_snapshot__lt=fecha_limite_detalle
            ).delete()
            
            if snapshots_eliminados_detalle[0] > 0:
                logger.info(f"🗑️ Snapshots detallados eliminados: {snapshots_eliminados_detalle[0]}")
            
            # Eliminar snapshots diarios antiguos (más de 90 días)
            # Pero mantener el primero de cada mes
            snapshots_diarios_antiguos = SnapshotDashboard.objects.filter(
                tipo='DIARIO',
                fecha_snapshot__lt=fecha_limite_diario
            ).exclude(
                fecha_snapshot__day=1  # Mantener primer día de cada mes
            )
            
            snapshots_eliminados_diarios = snapshots_diarios_antiguos.delete()
            
            if snapshots_eliminados_diarios[0] > 0:
                logger.info(f"🗑️ Snapshots diarios eliminados: {snapshots_eliminados_diarios[0]}")
                
        except Exception as e:
            logger.error(f"❌ Error en limpiar_snapshots_antiguos: {str(e)}")


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def crear_snapshot_dashboard(tipo='DIARIO'):
    """
    Crea un snapshot del dashboard actual con manejo correcto de tipos no-serializables
    
    Args:
        tipo: Tipo de snapshot (MINUTO, HORARIO, DIARIO, MENSUAL)
        
    Returns:
        bool: True si se creó correctamente, False en caso de error
    """
    try:
        from .generators import DashboardDataGenerator
        
        # Generar datos del dashboard
        generator = DashboardDataGenerator()
        dashboard_data = generator.generar_dashboard_completo()
        
        # Convertir TODOS los tipos no-serializables (Decimal, UUID, datetime) a tipos JSON-safe
        dashboard_data_limpio = convertir_a_json_serializable(dashboard_data)
        
        # Extraer métricas principales (ya convertidas)
        ventas = dashboard_data_limpio.get('ventas', {})
        inventario = dashboard_data_limpio.get('inventario', {})
        financiero = dashboard_data_limpio.get('financiero', {})
        
        # Crear snapshot con datos completamente limpios
        snapshot = SnapshotDashboard.objects.create(
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
            metricas_completas=dashboard_data_limpio  # ✅ Sin Decimals, UUID, datetime
        )
        
        logger.info(f"✅ Snapshot {tipo} creado exitosamente: ID {snapshot.id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al crear snapshot: {str(e)}", exc_info=True)
        return False


def notificar_alerta_critica(tipo_alerta, mensaje, datos=None):
    """
    Sistema de notificación de alertas críticas
    
    Args:
        tipo_alerta: Tipo de alerta (STOCK, VENCIMIENTO, CAJA, etc)
        mensaje: Mensaje de la alerta
        datos: Datos adicionales de contexto
    """
    try:
        # Convertir datos a formato JSON-safe
        if datos:
            datos = convertir_a_json_serializable(datos)
        
        logger.warning(f"🚨 ALERTA [{tipo_alerta}]: {mensaje}")
        if datos:
            logger.warning(f"📊 Datos: {datos}")
        
        # TODO: Implementar sistema de notificaciones
        # - Email
        # - Notificaciones push
        # - SMS
        # - Slack/Telegram
        
    except Exception as e:
        logger.error(f"❌ Error en notificar_alerta_critica: {str(e)}")


def generar_reporte_programado(tipo_reporte, configuracion):
    """
    Genera reportes de forma programada (para usar con Celery)
    
    Args:
        tipo_reporte: Tipo de reporte a generar
        configuracion: Configuración del reporte
        
    Returns:
        bool: True si se generó correctamente
    """
    try:
        logger.info(f"📊 Generando reporte programado: {tipo_reporte}")
        
        # Convertir configuración a formato JSON-safe
        configuracion_limpia = convertir_a_json_serializable(configuracion)
        
        # TODO: Implementar con Celery para ejecución asíncrona
        # from .tasks import generar_reporte_async
        # generar_reporte_async.delay(tipo_reporte, configuracion_limpia)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en generar_reporte_programado: {str(e)}")
        return False


# ============================================================================
# SEÑALES DE DEBUG Y MONITOREO
# ============================================================================

@receiver(post_save, sender=ConfiguracionReporte)
def log_configuracion_cambios(sender, instance, created, **kwargs):
    """Log de cambios en configuraciones"""
    try:
        if created:
            logger.info(
                f"📝 Nueva configuración creada: {instance.nombre_configuracion} "
                f"[{instance.tipo_reporte}] por usuario {instance.usuario.username}"
            )
        else:
            logger.info(
                f"✏️ Configuración actualizada: {instance.nombre_configuracion} "
                f"[{instance.tipo_reporte}]"
            )
    except Exception as e:
        logger.error(f"❌ Error en log_configuracion_cambios: {str(e)}")


@receiver(post_save, sender=SnapshotDashboard)
def log_snapshot_creado(sender, instance, created, **kwargs):
    """Log de creación de snapshots"""
    try:
        if created:
            logger.info(
                f"📸 Snapshot creado: {instance.tipo} - {instance.fecha_snapshot} "
                f"(Ventas: {instance.numero_ventas_dia} día, "
                f"Total: Bs. {instance.total_ventas_dia})"
            )
    except Exception as e:
        logger.error(f"❌ Error en log_snapshot_creado: {str(e)}")