"""
Tareas de Celery para el Sistema de Alertas de Stock
apps/stock_alert_system/tasks.py
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
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
    Tarea programada para verificar y actualizar las alertas de stock.
    
    Esta tarea:
    1. Revisa todos los productos y quintales activos
    2. Calcula su estado de stock actual
    3. Genera o actualiza alertas según corresponda
    4. Envía notificaciones si es necesario
    
    Returns:
        dict: Resumen de la ejecución con estadísticas
    """
    try:
        from apps.stock_alert_system.models import AlertaStock, EstadoStock, HistorialEstado
        from apps.inventory_management.models import Producto, Quintal
        from apps.stock_alert_system.status_calculator import StockStatusCalculator
        from apps.notifications.services.notification_service import NotificationService
        
        logger.info("Iniciando verificación de alertas de stock...")
        
        # Contadores para estadísticas
        stats = {
            'productos_revisados': 0,
            'quintales_revisados': 0,
            'alertas_creadas': 0,
            'alertas_actualizadas': 0,
            'notificaciones_enviadas': 0,
            'errores': 0
        }
        
        # ========== VERIFICAR PRODUCTOS ==========
        productos_activos = Producto.objects.filter(activo=True)
        
        for producto in productos_activos:
            try:
                stats['productos_revisados'] += 1
                
                # Calcular estado del stock
                calculator = StockStatusCalculator(producto)
                estado_info = calculator.calcular_estado()
                
                # Buscar o crear el estado del producto
                estado, created = EstadoStock.objects.get_or_create(
                    producto=producto,
                    defaults={
                        'estado_actual': estado_info['estado'],
                        'stock_actual': producto.stock_disponible,
                        'dias_restantes': estado_info.get('dias_restantes'),
                        'requiere_atencion': estado_info.get('requiere_atencion', False)
                    }
                )
                
                # Actualizar estado si no es nuevo
                if not created:
                    estado_anterior = estado.estado_actual
                    estado.estado_actual = estado_info['estado']
                    estado.stock_actual = producto.stock_disponible
                    estado.dias_restantes = estado_info.get('dias_restantes')
                    estado.requiere_atencion = estado_info.get('requiere_atencion', False)
                    estado.save()
                    
                    # Registrar cambio de estado si hubo uno
                    if estado_anterior != estado.estado_actual:
                        HistorialEstado.objects.create(
                            estado=estado,
                            estado_anterior=estado_anterior,
                            estado_nuevo=estado.estado_actual,
                            motivo='Actualización automática por tarea programada'
                        )
                
                # ========== GESTIONAR ALERTAS ==========
                if estado.requiere_atencion:
                    # Buscar alerta existente activa
                    alerta_existente = AlertaStock.objects.filter(
                        producto=producto,
                        estado='pendiente'
                    ).first()
                    
                    if alerta_existente:
                        # Actualizar alerta existente
                        alerta_existente.tipo_alerta = estado_info['tipo_alerta']
                        alerta_existente.prioridad = estado_info.get('prioridad', 'media')
                        alerta_existente.mensaje = estado_info.get('mensaje', '')
                        alerta_existente.save()
                        stats['alertas_actualizadas'] += 1
                    else:
                        # Crear nueva alerta
                        AlertaStock.objects.create(
                            producto=producto,
                            tipo_alerta=estado_info['tipo_alerta'],
                            prioridad=estado_info.get('prioridad', 'media'),
                            mensaje=estado_info.get('mensaje', ''),
                            stock_actual=producto.stock_disponible,
                            stock_minimo=producto.stock_minimo,
                            estado='pendiente'
                        )
                        stats['alertas_creadas'] += 1
                        
                        # Enviar notificación para nueva alerta crítica
                        if estado_info.get('prioridad') == 'alta':
                            try:
                                NotificationService.crear_notificacion(
                                    tipo='alerta_stock',
                                    titulo=f'⚠️ Alerta Crítica: {producto.nombre}',
                                    mensaje=estado_info.get('mensaje', ''),
                                    prioridad='alta',
                                    metadata={
                                        'producto_id': producto.id,
                                        'stock_actual': producto.stock_disponible,
                                        'tipo_alerta': estado_info['tipo_alerta']
                                    }
                                )
                                stats['notificaciones_enviadas'] += 1
                            except Exception as e:
                                logger.error(f"Error al enviar notificación para producto {producto.id}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error al procesar producto {producto.id}: {str(e)}")
                stats['errores'] += 1
                continue
        
        # ========== VERIFICAR QUINTALES ==========
        quintales_activos = Quintal.objects.filter(activo=True, vendido=False)
        
        for quintal in quintales_activos:
            try:
                stats['quintales_revisados'] += 1
                
                # Calcular estado del quintal
                calculator = StockStatusCalculator(quintal)
                estado_info = calculator.calcular_estado()
                
                # Buscar o crear el estado del quintal
                estado, created = EstadoStock.objects.get_or_create(
                    quintal=quintal,
                    defaults={
                        'estado_actual': estado_info['estado'],
                        'stock_actual': quintal.peso_actual,
                        'dias_restantes': estado_info.get('dias_restantes'),
                        'requiere_atencion': estado_info.get('requiere_atencion', False)
                    }
                )
                
                # Actualizar estado si no es nuevo
                if not created:
                    estado_anterior = estado.estado_actual
                    estado.estado_actual = estado_info['estado']
                    estado.stock_actual = quintal.peso_actual
                    estado.dias_restantes = estado_info.get('dias_restantes')
                    estado.requiere_atencion = estado_info.get('requiere_atencion', False)
                    estado.save()
                    
                    # Registrar cambio de estado si hubo uno
                    if estado_anterior != estado.estado_actual:
                        HistorialEstado.objects.create(
                            estado=estado,
                            estado_anterior=estado_anterior,
                            estado_nuevo=estado.estado_actual,
                            motivo='Actualización automática por tarea programada'
                        )
                
                # ========== GESTIONAR ALERTAS ==========
                if estado.requiere_atencion:
                    # Buscar alerta existente activa
                    alerta_existente = AlertaStock.objects.filter(
                        quintal=quintal,
                        estado='pendiente'
                    ).first()
                    
                    if alerta_existente:
                        # Actualizar alerta existente
                        alerta_existente.tipo_alerta = estado_info['tipo_alerta']
                        alerta_existente.prioridad = estado_info.get('prioridad', 'media')
                        alerta_existente.mensaje = estado_info.get('mensaje', '')
                        alerta_existente.save()
                        stats['alertas_actualizadas'] += 1
                    else:
                        # Crear nueva alerta
                        AlertaStock.objects.create(
                            quintal=quintal,
                            tipo_alerta=estado_info['tipo_alerta'],
                            prioridad=estado_info.get('prioridad', 'media'),
                            mensaje=estado_info.get('mensaje', ''),
                            stock_actual=quintal.peso_actual,
                            estado='pendiente'
                        )
                        stats['alertas_creadas'] += 1
                        
                        # Enviar notificación para nueva alerta crítica
                        if estado_info.get('prioridad') == 'alta':
                            try:
                                NotificationService.crear_notificacion(
                                    tipo='alerta_stock',
                                    titulo=f'⚠️ Alerta Crítica: Quintal {quintal.codigo}',
                                    mensaje=estado_info.get('mensaje', ''),
                                    prioridad='alta',
                                    metadata={
                                        'quintal_id': quintal.id,
                                        'peso_actual': float(quintal.peso_actual),
                                        'tipo_alerta': estado_info['tipo_alerta']
                                    }
                                )
                                stats['notificaciones_enviadas'] += 1
                            except Exception as e:
                                logger.error(f"Error al enviar notificación para quintal {quintal.id}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error al procesar quintal {quintal.id}: {str(e)}")
                stats['errores'] += 1
                continue
        
        # ========== LIMPIAR ALERTAS ANTIGUAS RESUELTAS ==========
        # Archivar alertas resueltas de más de 30 días
        fecha_limite = timezone.now() - timezone.timedelta(days=30)
        alertas_antiguas = AlertaStock.objects.filter(
            estado='resuelta',
            fecha_resolucion__lt=fecha_limite
        )
        alertas_archivadas = alertas_antiguas.update(estado='archivada')
        
        if alertas_archivadas > 0:
            logger.info(f"Se archivaron {alertas_archivadas} alertas antiguas resueltas")
        
        # ========== RESUMEN FINAL ==========
        logger.info(f"""
        ✅ Verificación de alertas completada exitosamente:
        - Productos revisados: {stats['productos_revisados']}
        - Quintales revisados: {stats['quintales_revisados']}
        - Alertas creadas: {stats['alertas_creadas']}
        - Alertas actualizadas: {stats['alertas_actualizadas']}
        - Notificaciones enviadas: {stats['notificaciones_enviadas']}
        - Alertas archivadas: {alertas_archivadas}
        - Errores: {stats['errores']}
        """)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error crítico en check_stock_alerts: {str(e)}")
        # Reintentar la tarea si falla
        raise self.retry(exc=e)


@shared_task(
    name='apps.stock_alert_system.tasks.send_daily_stock_summary',
    bind=True
)
def send_daily_stock_summary(self):
    """
    Envía un resumen diario del estado del inventario.
    
    Esta tarea genera y envía un informe con:
    - Alertas activas por prioridad
    - Productos con stock crítico
    - Quintales próximos a vencer
    - Estadísticas generales
    """
    try:
        from apps.stock_alert_system.models import AlertaStock, EstadoStock
        from apps.notifications.services.notification_service import NotificationService
        
        logger.info("Generando resumen diario de stock...")
        
        # Contar alertas por prioridad
        alertas_altas = AlertaStock.objects.filter(estado='pendiente', prioridad='alta').count()
        alertas_medias = AlertaStock.objects.filter(estado='pendiente', prioridad='media').count()
        alertas_bajas = AlertaStock.objects.filter(estado='pendiente', prioridad='baja').count()
        
        # Contar estados que requieren atención
        estados_criticos = EstadoStock.objects.filter(
            requiere_atencion=True,
            estado_actual__in=['critico', 'muy_bajo']
        ).count()
        
        # Crear mensaje del resumen
        mensaje = f"""
        📊 Resumen Diario de Inventario
        
        🔴 Alertas de Alta Prioridad: {alertas_altas}
        🟡 Alertas de Media Prioridad: {alertas_medias}
        🟢 Alertas de Baja Prioridad: {alertas_bajas}
        
        ⚠️ Estados Críticos: {estados_criticos}
        
        Total de Alertas Pendientes: {alertas_altas + alertas_medias + alertas_bajas}
        """
        
        # Enviar notificación solo si hay alertas o estados críticos
        if alertas_altas > 0 or estados_criticos > 0:
            NotificationService.crear_notificacion(
                tipo='reporte_diario',
                titulo='📊 Resumen Diario de Inventario',
                mensaje=mensaje,
                prioridad='media' if alertas_altas > 0 else 'baja'
            )
            logger.info("Resumen diario enviado exitosamente")
        else:
            logger.info("No hay alertas activas para el resumen diario")
        
        return {
            'alertas_altas': alertas_altas,
            'alertas_medias': alertas_medias,
            'alertas_bajas': alertas_bajas,
            'estados_criticos': estados_criticos
        }
        
    except Exception as e:
        logger.error(f"Error al generar resumen diario: {str(e)}")
        raise


@shared_task(
    name='apps.stock_alert_system.tasks.cleanup_old_alerts',
    bind=True
)
def cleanup_old_alerts(self):
    """
    Limpia alertas antiguas del sistema.
    
    Elimina:
    - Alertas archivadas de más de 90 días
    - Alertas resueltas de más de 60 días
    """
    try:
        from apps.stock_alert_system.models import AlertaStock
        from django.utils import timezone
        
        logger.info("Iniciando limpieza de alertas antiguas...")
        
        # Eliminar alertas archivadas muy antiguas (90 días)
        fecha_archivo = timezone.now() - timezone.timedelta(days=90)
        alertas_eliminadas_archivo = AlertaStock.objects.filter(
            estado='archivada',
            fecha_creacion__lt=fecha_archivo
        ).delete()[0]
        
        # Archivar alertas resueltas antiguas (60 días)
        fecha_resolucion = timezone.now() - timezone.timedelta(days=60)
        alertas_archivadas = AlertaStock.objects.filter(
            estado='resuelta',
            fecha_resolucion__lt=fecha_resolucion
        ).update(estado='archivada')
        
        logger.info(f"""
        🗑️ Limpieza de alertas completada:
        - Alertas eliminadas: {alertas_eliminadas_archivo}
        - Alertas archivadas: {alertas_archivadas}
        """)
        
        return {
            'alertas_eliminadas': alertas_eliminadas_archivo,
            'alertas_archivadas': alertas_archivadas
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de alertas: {str(e)}")
        raise


@shared_task(
    name='apps.stock_alert_system.tasks.recalculate_all_stock_status',
    bind=True
)
def recalculate_all_stock_status(self):
    """
    Recalcula el estado de stock de todos los productos y quintales.
    
    Esta tarea se usa típicamente después de:
    - Cambios masivos en el inventario
    - Correcciones de datos
    - Mantenimiento del sistema
    """
    try:
        from apps.stock_alert_system.models import EstadoStock
        from apps.inventory_management.models import Producto, Quintal
        from apps.stock_alert_system.status_calculator import StockStatusCalculator
        
        logger.info("Iniciando recálculo completo de estados de stock...")
        
        # Limpiar todos los estados existentes
        EstadoStock.objects.all().delete()
        
        estados_creados = 0
        
        # Recalcular para todos los productos activos
        for producto in Producto.objects.filter(activo=True):
            try:
                calculator = StockStatusCalculator(producto)
                estado_info = calculator.calcular_estado()
                
                EstadoStock.objects.create(
                    producto=producto,
                    estado_actual=estado_info['estado'],
                    stock_actual=producto.stock_disponible,
                    dias_restantes=estado_info.get('dias_restantes'),
                    requiere_atencion=estado_info.get('requiere_atencion', False)
                )
                estados_creados += 1
            except Exception as e:
                logger.error(f"Error al recalcular producto {producto.id}: {str(e)}")
        
        # Recalcular para todos los quintales activos no vendidos
        for quintal in Quintal.objects.filter(activo=True, vendido=False):
            try:
                calculator = StockStatusCalculator(quintal)
                estado_info = calculator.calcular_estado()
                
                EstadoStock.objects.create(
                    quintal=quintal,
                    estado_actual=estado_info['estado'],
                    stock_actual=quintal.peso_actual,
                    dias_restantes=estado_info.get('dias_restantes'),
                    requiere_atencion=estado_info.get('requiere_atencion', False)
                )
                estados_creados += 1
            except Exception as e:
                logger.error(f"Error al recalcular quintal {quintal.id}: {str(e)}")
        
        logger.info(f"✅ Recálculo completo finalizado. Estados creados: {estados_creados}")
        
        return {'estados_creados': estados_creados}
        
    except Exception as e:
        logger.error(f"Error en recálculo completo de estados: {str(e)}")
        raise