from celery import shared_task
import logging
from .models import Notificacion
from .services.notification_service import NotificationService

logger = logging.getLogger('commercebox')

@shared_task(name='apps.notifications.tasks.procesar_notificaciones_pendientes')
def procesar_notificaciones_pendientes():
    """
    Tarea para procesar notificaciones que quedaron en estado pendiente.
    Por ahora solo marca como enviadas las que no son push,
    o gatilla los envíos externos si estuvieran configurados.
    """
    try:
        # En una versión futura aquí se podrían enviar emails, SMS, etc.
        notificaciones = Notificacion.objects.exclude(estado='LEIDA')
        count = notificaciones.count()
        if count > 0:
            logger.info(f"Procesando {count} notificaciones pendientes")
            # Por ahora no hacemos nada externo, solo reportamos
        return {"processed": count}
    except Exception as e:
        logger.error(f"Error procesando notificaciones: {str(e)}")
        return {"error": str(e)}
