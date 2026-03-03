"""
Tareas de Celery para el Sistema de Alertas de Stock
apps/stock_alert_system/tasks.py
"""
from celery import shared_task
import logging

logger = logging.getLogger('commercebox')


@shared_task(
    name='apps.stock_alert_system.tasks.check_stock_alerts',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutos
)
def check_stock_alerts(self):
    """
    Tarea programada para verificar y actualizar las alertas de stock de todo el sistema.
    Utiliza el StatusCalculator para procesar productos, quintales y vencimientos.
    """
    try:
        from apps.stock_alert_system.status_calculator import StatusCalculator, AlertaManager
        
        logger.info("Iniciando verificación masiva de estados de stock...")
        
        # 1. Recalcular estados de todos los productos (incluye quintales y alertas)
        count = StatusCalculator.calcular_todos_los_productos()
        
        # 2. Gestionar automatización de alertas
        # Resuelve alertas que ya no son relevantes y limpia antiguas
        AlertaManager.resolver_alertas_automaticamente()
        AlertaManager.limpiar_alertas_antiguas(dias=30)
        
        logger.info(f"Verificación completada. Se procesaron {count} productos.")
        
        return {
            'status': 'success',
            'productos_procesados': count,
            'mensaje': 'Verificación de stock completada exitosamente'
        }
    except Exception as e:
        logger.error(f"Error crítico en tarea check_stock_alerts: {str(e)}", exc_info=True)
        # Reintentar en caso de error temporal
        self.retry(exc=e)