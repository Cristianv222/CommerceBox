# apps/notifications/services/notification_service.py

"""
Servicio Principal de Notificaciones
Genera y envía notificaciones a través de diferentes canales
"""

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Servicio centralizado para crear y gestionar notificaciones
    """
    
    # =========================================================================
    # MÉTODOS PRINCIPALES
    # =========================================================================
    
    @staticmethod
    def crear_notificacion(
        tipo_codigo,
        usuario,
        titulo,
        mensaje,
        prioridad='MEDIA',
        objeto_relacionado=None,
        url_accion='',
        datos_adicionales=None,
        requiere_accion=False
    ):
        """
        Método genérico para crear una notificación
        
        Args:
            tipo_codigo: Código del tipo de notificación
            usuario: Usuario destinatario
            titulo: Título de la notificación
            mensaje: Mensaje descriptivo
            prioridad: BAJA, MEDIA, ALTA, CRITICA
            objeto_relacionado: Objeto relacionado (Quintal, ProductoNormal, etc)
            url_accion: URL para ver detalles
            datos_adicionales: Dict con datos extra
            requiere_accion: Boolean si requiere acción del usuario
        
        Returns:
            Notificacion: Instancia creada
        """
        from apps.notifications.models import (
            Notificacion, TipoNotificacion, 
            PreferenciasNotificacion, ConfiguracionNotificacion
        )
        
        # Verificar si el sistema está activo
        config = ConfiguracionNotificacion.get_config()
        if not config.notificaciones_activas:
            return None
        
        # Obtener tipo de notificación
        try:
            tipo_notif = TipoNotificacion.objects.get(codigo=tipo_codigo, activo=True)
        except TipoNotificacion.DoesNotExist:
            logger.warning(f"Tipo de notificación '{tipo_codigo}' no existe")
            return None
        
        # Verificar preferencias del usuario
        try:
            preferencias = usuario.preferencias_notificaciones
        except PreferenciasNotificacion.DoesNotExist:
            # Crear preferencias por defecto si no existen
            preferencias = PreferenciasNotificacion.objects.create(usuario=usuario)
        
        if not preferencias.puede_recibir_notificacion(tipo_notif, prioridad):
            logger.info(f"Usuario {usuario.username} tiene desactivadas notificaciones del tipo {tipo_codigo}")
            return None
        
        # Crear notificación
        notificacion = Notificacion.objects.create(
            tipo_notificacion=tipo_notif,
            usuario=usuario,
            titulo=titulo,
            mensaje=mensaje,
            prioridad=prioridad,
            requiere_accion=requiere_accion,
            url_accion=url_accion,
            datos_adicionales=datos_adicionales or {},
            estado='PENDIENTE'
        )
        
        # Asociar objeto relacionado si existe
        if objeto_relacionado:
            content_type = ContentType.objects.get_for_model(objeto_relacionado)
            notificacion.content_type = content_type
            notificacion.object_id = objeto_relacionado.pk
            notificacion.save()
        
        # Enviar por diferentes canales
        NotificationService._enviar_notificacion(notificacion, preferencias, config)
        
        return notificacion
    
    @staticmethod
    def _enviar_notificacion(notificacion, preferencias, config):
        """
        Envía la notificación por los canales configurados
        """
        # Web (siempre se guarda en BD)
        notificacion.enviada_web = True
        
        # Email
        if preferencias.recibir_notificaciones_email and config.email_activo:
            if notificacion.tipo_notificacion.enviar_email:
                NotificationService._enviar_email(notificacion)
        
        # Push (futuro)
        if preferencias.recibir_notificaciones_push and config.push_activo:
            if notificacion.tipo_notificacion.enviar_push:
                NotificationService._enviar_push(notificacion)
        
        # SMS (futuro)
        if preferencias.recibir_notificaciones_sms and config.sms_activo:
            if notificacion.tipo_notificacion.enviar_sms:
                NotificationService._enviar_sms(notificacion)
        
        # Actualizar estado
        notificacion.estado = 'ENVIADA'
        notificacion.fecha_envio = timezone.now()
        notificacion.save()
    
    @staticmethod
    def _enviar_email(notificacion):
        """Envía notificación por email"""
        from django.core.mail import send_mail
        from apps.notifications.models import ConfiguracionNotificacion, LogNotificacion
        
        config = ConfiguracionNotificacion.get_config()
        
        try:
            tiempo_inicio = timezone.now()
            
            send_mail(
                subject=notificacion.titulo,
                message=notificacion.mensaje,
                from_email=config.email_remitente or 'noreply@commercebox.com',
                recipient_list=[notificacion.usuario.email],
                fail_silently=False,
            )
            
            tiempo_fin = timezone.now()
            tiempo_respuesta = (tiempo_fin - tiempo_inicio).total_seconds()
            
            # Log exitoso
            LogNotificacion.objects.create(
                notificacion=notificacion,
                canal='EMAIL',
                resultado='EXITOSO',
                destinatario=notificacion.usuario.email,
                tiempo_respuesta=Decimal(str(tiempo_respuesta))
            )
            
            notificacion.enviada_email = True
            notificacion.save()
            
            logger.info(f"Email enviado a {notificacion.usuario.email}")
            
        except Exception as e:
            logger.error(f"Error al enviar email: {str(e)}")
            
            # Log de error
            LogNotificacion.objects.create(
                notificacion=notificacion,
                canal='EMAIL',
                resultado='ERROR',
                destinatario=notificacion.usuario.email,
                mensaje_error=str(e)
            )
            
            notificacion.intentos_envio += 1
            notificacion.error_mensaje = str(e)
            notificacion.save()
    
    @staticmethod
    def _enviar_push(notificacion):
        """Envía notificación push (implementación futura)"""
        # TODO: Integrar con servicio de push notifications
        # Ejemplo: Firebase Cloud Messaging, OneSignal, etc
        pass
    
    @staticmethod
    def _enviar_sms(notificacion):
        """Envía notificación SMS (implementación futura)"""
        # TODO: Integrar con proveedor de SMS
        # Ejemplo: Twilio, AWS SNS, etc
        pass
    
    # =========================================================================
    # NOTIFICACIONES DE STOCK - QUINTALES
    # =========================================================================
    
    @staticmethod
    def crear_notificacion_stock_critico_quintal(quintal, porcentaje_restante):
        """Notifica que un quintal está en estado crítico"""
        from apps.authentication.models import Usuario
        
        # Notificar a supervisores y administradores
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"🚨 Quintal Crítico: {quintal.producto.nombre}"
        mensaje = (
            f"El quintal {quintal.codigo_quintal} está en estado CRÍTICO.\n\n"
            f"📦 Producto: {quintal.producto.nombre}\n"
            f"⚖️ Peso restante: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}\n"
            f"📊 Porcentaje: {porcentaje_restante:.1f}%\n"
            f"🏪 Proveedor: {quintal.proveedor.nombre_comercial}\n\n"
            f"⚠️ Se recomienda evaluar reorden inmediato."
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='STOCK_CRITICO_QUINTAL',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='CRITICA',
                objeto_relacionado=quintal,
                url_accion=f'/inventory/quintal/{quintal.id}/',
                datos_adicionales={
                    'quintal_id': str(quintal.id),
                    'quintal_codigo': quintal.codigo_quintal,
                    'producto_id': str(quintal.producto.id),
                    'producto_nombre': quintal.producto.nombre,
                    'peso_actual': float(quintal.peso_actual),
                    'porcentaje_restante': float(porcentaje_restante)
                },
                requiere_accion=True
            )
    
    @staticmethod
    def crear_notificacion_quintal_agotado(quintal):
        """Notifica que un quintal se agotó completamente"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"⚫ Quintal Agotado: {quintal.producto.nombre}"
        mensaje = (
            f"El quintal {quintal.codigo_quintal} se ha AGOTADO completamente.\n\n"
            f"📦 Producto: {quintal.producto.nombre}\n"
            f"🏪 Proveedor: {quintal.proveedor.nombre_comercial}\n"
            f"📅 Fecha recepción: {quintal.fecha_recepcion.strftime('%d/%m/%Y')}\n"
            f"⚖️ Peso inicial: {quintal.peso_inicial} {quintal.unidad_medida.abreviatura}\n\n"
            f"✅ Quintal completamente vendido."
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='QUINTAL_AGOTADO',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='MEDIA',
                objeto_relacionado=quintal,
                datos_adicionales={
                    'quintal_id': str(quintal.id),
                    'producto_nombre': quintal.producto.nombre
                }
            )
    
    @staticmethod
    def crear_notificacion_vencimiento_proximo(quintal, dias_restantes):
        """Notifica que un quintal está próximo a vencer"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"⏰ Vencimiento Próximo: {quintal.producto.nombre}"
        mensaje = (
            f"El quintal {quintal.codigo_quintal} está próximo a vencer.\n\n"
            f"📦 Producto: {quintal.producto.nombre}\n"
            f"📅 Fecha vencimiento: {quintal.fecha_vencimiento.strftime('%d/%m/%Y')}\n"
            f"⏰ Días restantes: {dias_restantes} día(s)\n"
            f"⚖️ Peso disponible: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}\n\n"
            f"⚠️ Considere promociones o descuentos para vender antes del vencimiento."
        )
        
        prioridad = 'CRITICA' if dias_restantes <= 2 else 'ALTA'
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='VENCIMIENTO_PROXIMO',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad=prioridad,
                objeto_relacionado=quintal,
                datos_adicionales={
                    'quintal_id': str(quintal.id),
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': quintal.fecha_vencimiento.isoformat()
                },
                requiere_accion=True
            )
    
    # =========================================================================
    # NOTIFICACIONES DE STOCK - PRODUCTOS NORMALES
    # =========================================================================
    
    @staticmethod
    def crear_notificacion_stock_critico(producto_normal):
        """Notifica que un producto normal está en stock crítico"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"🔴 Stock Crítico: {producto_normal.producto.nombre}"
        mensaje = (
            f"El producto {producto_normal.producto.nombre} está en STOCK CRÍTICO.\n\n"
            f"📦 Stock actual: {producto_normal.stock_actual} unidades\n"
            f"⚠️ Stock mínimo: {producto_normal.stock_minimo} unidades\n"
            f"📊 Estado: {producto_normal.estado_stock()}\n\n"
            f"🚨 ACCIÓN REQUERIDA: Realizar reorden urgente."
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='STOCK_CRITICO',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='CRITICA',
                objeto_relacionado=producto_normal,
                url_accion=f'/inventory/producto/{producto_normal.producto.id}/',
                datos_adicionales={
                    'producto_id': str(producto_normal.producto.id),
                    'producto_nombre': producto_normal.producto.nombre,
                    'stock_actual': producto_normal.stock_actual,
                    'stock_minimo': producto_normal.stock_minimo
                },
                requiere_accion=True
            )
    
    @staticmethod
    def crear_notificacion_stock_bajo(producto_normal):
        """Notifica que un producto normal está en stock bajo"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"🟡 Stock Bajo: {producto_normal.producto.nombre}"
        mensaje = (
            f"El producto {producto_normal.producto.nombre} tiene stock BAJO.\n\n"
            f"📦 Stock actual: {producto_normal.stock_actual} unidades\n"
            f"⚠️ Stock mínimo: {producto_normal.stock_minimo} unidades\n\n"
            f"💡 Se recomienda planificar reorden pronto."
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='STOCK_BAJO',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='ALTA',
                objeto_relacionado=producto_normal,
                datos_adicionales={
                    'producto_id': str(producto_normal.producto.id),
                    'stock_actual': producto_normal.stock_actual
                }
            )
    
    @staticmethod
    def crear_notificacion_stock_agotado(producto_normal):
        """Notifica que un producto normal está agotado"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"⚫ Stock Agotado: {producto_normal.producto.nombre}"
        mensaje = (
            f"El producto {producto_normal.producto.nombre} está AGOTADO.\n\n"
            f"📦 Stock actual: 0 unidades\n"
            f"⚠️ Stock mínimo: {producto_normal.stock_minimo} unidades\n\n"
            f"🚨 Reorden URGENTE necesario."
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='STOCK_AGOTADO',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='CRITICA',
                objeto_relacionado=producto_normal,
                url_accion=f'/inventory/producto/{producto_normal.producto.id}/',
                datos_adicionales={
                    'producto_id': str(producto_normal.producto.id),
                    'producto_nombre': producto_normal.producto.nombre
                },
                requiere_accion=True
            )
    
    # =========================================================================
    # NOTIFICACIONES DE VENTAS
    # =========================================================================
    
    @staticmethod
    def crear_notificacion_venta_grande(venta):
        """Notifica una venta de monto grande"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        cliente_nombre = venta.cliente.nombre_completo() if venta.cliente else 'Cliente Mostrador'
        
        titulo = f"💰 Venta Grande: ${venta.total}"
        mensaje = (
            f"Se ha realizado una venta de monto significativo.\n\n"
            f"🧾 Número: {venta.numero_venta}\n"
            f"👤 Cliente: {cliente_nombre}\n"
            f"💵 Total: ${venta.total}\n"
            f"👨‍💼 Vendedor: {venta.vendedor.get_full_name()}\n"
            f"📅 Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}\n"
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='VENTA_GRANDE',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='ALTA',
                objeto_relacionado=venta,
                url_accion=f'/sales/venta/{venta.id}/',
                datos_adicionales={
                    'venta_id': str(venta.id),
                    'numero_venta': venta.numero_venta,
                    'total': float(venta.total),
                    'cliente': cliente_nombre
                }
            )
    
    @staticmethod
    def crear_notificacion_descuento_excesivo(detalle_venta):
        """Notifica cuando se aplica un descuento excesivo"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"⚠️ Descuento Excesivo: {detalle_venta.descuento_porcentaje}%"
        mensaje = (
            f"Se ha aplicado un descuento excesivo en una venta.\n\n"
            f"🧾 Venta: {detalle_venta.venta.numero_venta}\n"
            f"📦 Producto: {detalle_venta.producto.nombre}\n"
            f"💸 Descuento: {detalle_venta.descuento_porcentaje}%\n"
            f"💵 Monto descuento: ${detalle_venta.descuento_monto}\n"
            f"👨‍💼 Vendedor: {detalle_venta.venta.vendedor.get_full_name()}\n"
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='DESCUENTO_EXCESIVO',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='ALTA',
                objeto_relacionado=detalle_venta.venta,
                datos_adicionales={
                    'venta_id': str(detalle_venta.venta.id),
                    'descuento_porcentaje': float(detalle_venta.descuento_porcentaje),
                    'producto': detalle_venta.producto.nombre
                },
                requiere_accion=True
            )
    
    @staticmethod
    def crear_notificacion_devolucion(devolucion):
        """Notifica sobre una devolución"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        titulo = f"↩️ Devolución: {devolucion.numero_devolucion}"
        mensaje = (
            f"Se ha registrado una devolución.\n\n"
            f"🔄 Número: {devolucion.numero_devolucion}\n"
            f"🧾 Venta original: {devolucion.venta_original.numero_venta}\n"
            f"💵 Monto: ${devolucion.monto_devolucion}\n"
            f"📋 Motivo: {devolucion.get_motivo_display()}\n"
            f"📝 Descripción: {devolucion.descripcion}\n"
            f"👤 Solicitado por: {devolucion.usuario_solicita.get_full_name()}\n"
        )
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='DEVOLUCION',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad='ALTA',
                objeto_relacionado=devolucion,
                url_accion=f'/sales/devolucion/{devolucion.id}/',
                datos_adicionales={
                    'devolucion_id': str(devolucion.id),
                    'monto': float(devolucion.monto_devolucion),
                    'motivo': devolucion.motivo
                },
                requiere_accion=True
            )
    
    # =========================================================================
    # NOTIFICACIONES DESDE ALERTAS
    # =========================================================================
    
    @staticmethod
    def crear_notificacion_desde_alerta(alerta):
        """Crea notificación desde una AlertaStock"""
        from apps.authentication.models import Usuario
        
        # Determinar usuarios según prioridad
        if alerta.prioridad == 'CRITICA':
            usuarios = Usuario.objects.filter(
                rol__codigo='ADMIN',
                estado='ACTIVO'
            )
        else:
            usuarios = Usuario.objects.filter(
                rol__codigo__in=['ADMIN', 'SUPERVISOR'],
                estado='ACTIVO'
            )
        
        # Mapear tipo de alerta a tipo de notificación
        tipo_codigo_map = {
            'STOCK_BAJO': 'STOCK_BAJO',
            'STOCK_CRITICO': 'STOCK_CRITICO',
            'STOCK_AGOTADO': 'STOCK_AGOTADO',
            'QUINTAL_CRITICO': 'STOCK_CRITICO_QUINTAL',
            'QUINTAL_AGOTADO': 'QUINTAL_AGOTADO',
            'VENCIMIENTO_PROXIMO': 'VENCIMIENTO_PROXIMO',
        }
        
        tipo_codigo = tipo_codigo_map.get(alerta.tipo_alerta, 'ALERTA_SISTEMA')
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo=tipo_codigo,
                usuario=usuario,
                titulo=alerta.titulo,
                mensaje=alerta.mensaje,
                prioridad=alerta.prioridad,
                objeto_relacionado=alerta,
                datos_adicionales=alerta.datos_adicionales,
                requiere_accion=True
            )
    
    @staticmethod
    def crear_notificacion_cambio_estado_stock(estado_stock, estado_anterior):
        """Notifica cambio de estado de stock"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        emoji_estado = estado_stock.get_icono_semaforo()
        
        titulo = f"{emoji_estado} Cambio de Estado: {estado_stock.producto.nombre}"
        mensaje = (
            f"El estado de stock ha cambiado.\n\n"
            f"📦 Producto: {estado_stock.producto.nombre}\n"
            f"📊 Estado anterior: {estado_anterior}\n"
            f"📊 Estado nuevo: {estado_stock.get_estado_semaforo_display()}\n"
        )
        
        if estado_stock.tipo_inventario == 'QUINTAL':
            mensaje += f"⚖️ Peso disponible: {estado_stock.peso_total_disponible} kg\n"
        else:
            mensaje += f"📦 Stock actual: {estado_stock.stock_actual} unidades\n"
        
        prioridad = 'CRITICA' if estado_stock.estado_semaforo == 'CRITICO' else 'ALTA'
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='CAMBIO_ESTADO_STOCK',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                prioridad=prioridad,
                objeto_relacionado=estado_stock,
                datos_adicionales={
                    'estado_anterior': estado_anterior,
                    'estado_nuevo': estado_stock.estado_semaforo,
                    'producto_id': str(estado_stock.producto.id)
                }
            )
    
    # =========================================================================
    # NOTIFICACIONES DE SISTEMA
    # =========================================================================
    
    @staticmethod
    def crear_notificacion_error_sistema(mensaje, detalles=''):
        """Notifica errores del sistema"""
        from apps.authentication.models import Usuario
        
        usuarios = Usuario.objects.filter(
            rol__codigo='ADMIN',
            estado='ACTIVO'
        )
        
        titulo = "🚨 Error del Sistema"
        mensaje_completo = f"{mensaje}\n\n{detalles}" if detalles else mensaje
        
        for usuario in usuarios:
            NotificationService.crear_notificacion(
                tipo_codigo='ERROR_SISTEMA',
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje_completo,
                prioridad='CRITICA',
                datos_adicionales={'error': mensaje, 'detalles': detalles},
                requiere_accion=True
            )