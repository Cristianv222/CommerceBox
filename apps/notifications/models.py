# apps/notifications/models.py

"""
Sistema de Notificaciones de CommerceBox
Gestiona alertas, notificaciones push, emails y notificaciones en tiempo real
"""

import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


# ============================================================================
# CONFIGURACIÓN DE NOTIFICACIONES
# ============================================================================

class ConfiguracionNotificacion(models.Model):
    """
    Configuración global del sistema de notificaciones
    Singleton pattern - solo un registro
    """
    
    # ==========================================
    # CANALES DE NOTIFICACIÓN
    # ==========================================
    notificaciones_activas = models.BooleanField(
        default=True,
        help_text='Sistema de notificaciones activo globalmente'
    )
    
    # Email
    email_activo = models.BooleanField(
        default=True,
        help_text='Enviar notificaciones por email'
    )
    email_host = models.CharField(max_length=255, blank=True, default='smtp.gmail.com')
    email_puerto = models.IntegerField(default=587)
    email_usuario = models.EmailField(blank=True)
    email_password = models.CharField(max_length=255, blank=True)
    email_remitente = models.EmailField(blank=True)
    
    # SMS (Futuro)
    sms_activo = models.BooleanField(
        default=False,
        help_text='Enviar notificaciones SMS (requiere integración)'
    )
    sms_proveedor = models.CharField(max_length=50, blank=True)
    sms_api_key = models.CharField(max_length=255, blank=True)
    
    # Push Notifications (Futuro)
    push_activo = models.BooleanField(
        default=False,
        help_text='Enviar notificaciones push'
    )
    
    # ==========================================
    # NOTIFICACIONES POR TIPO
    # ==========================================
    # Stock
    notif_stock_critico = models.BooleanField(default=True)
    notif_stock_bajo = models.BooleanField(default=True)
    notif_stock_agotado = models.BooleanField(default=True)
    notif_vencimiento_proximo = models.BooleanField(default=True)
    
    # Ventas
    notif_venta_grande = models.BooleanField(default=True)
    notif_venta_grande_monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500,
        help_text='Monto mínimo para notificar venta grande'
    )
    notif_descuento_excesivo = models.BooleanField(default=True)
    notif_descuento_excesivo_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20,
        help_text='% de descuento para generar alerta'
    )
    notif_devolucion = models.BooleanField(default=True)
    
    # Financiero
    notif_caja_chica_baja = models.BooleanField(default=True)
    notif_caja_chica_limite = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50,
        help_text='Monto mínimo de caja chica para alertar'
    )
    notif_diferencia_arqueo = models.BooleanField(default=True)
    notif_diferencia_arqueo_monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10,
        help_text='Diferencia mínima en arqueo para alertar'
    )
    
    # Sistema
    notif_error_sistema = models.BooleanField(default=True)
    notif_backup_completado = models.BooleanField(default=True)
    notif_hardware_error = models.BooleanField(default=True)
    
    # ==========================================
    # DESTINATARIOS
    # ==========================================
    emails_administradores = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de emails de administradores'
    )
    emails_supervisores = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de emails de supervisores'
    )
    
    # ==========================================
    # AUDITORÍA
    # ==========================================
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configuraciones_notificaciones'
    )
    
    class Meta:
        verbose_name = 'Configuración de Notificaciones'
        verbose_name_plural = 'Configuraciones de Notificaciones'
        db_table = 'notif_configuracion'
    
    def __str__(self):
        estado = "Activo" if self.notificaciones_activas else "Inactivo"
        return f"Configuración de Notificaciones ({estado})"
    
    def save(self, *args, **kwargs):
        """Asegurar que solo exista un registro (Singleton)"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Obtiene o crea la configuración única del sistema"""
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'notificaciones_activas': True,
                'email_activo': True,
                'notif_stock_critico': True,
                'notif_stock_bajo': True,
                'notif_stock_agotado': True,
                'notif_venta_grande': True,
                'notif_devolucion': True,
            }
        )
        return config


# ============================================================================
# TIPOS DE NOTIFICACIÓN
# ============================================================================

class TipoNotificacion(models.Model):
    """
    Catálogo de tipos de notificaciones del sistema
    """
    
    CATEGORIA_CHOICES = [
        ('STOCK', '📦 Stock e Inventario'),
        ('VENTAS', '🛒 Ventas'),
        ('FINANCIERO', '💰 Financiero'),
        ('SISTEMA', '⚙️ Sistema'),
        ('USUARIO', '👤 Usuario'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text='Código único del tipo de notificación (ej: STOCK_CRITICO)'
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    # Clasificación
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        db_index=True
    )
    prioridad_default = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='MEDIA'
    )
    
    # Plantilla
    plantilla_titulo = models.CharField(
        max_length=200,
        help_text='Plantilla con variables: {producto}, {cantidad}, etc'
    )
    plantilla_mensaje = models.TextField(
        help_text='Plantilla HTML o texto para el mensaje'
    )
    
    # Configuración
    requiere_accion = models.BooleanField(
        default=False,
        help_text='La notificación requiere acción del usuario'
    )
    enviar_email = models.BooleanField(default=False)
    enviar_push = models.BooleanField(default=False)
    enviar_sms = models.BooleanField(default=False)
    
    # Roles que reciben esta notificación
    roles_destinatarios = models.JSONField(
        default=list,
        help_text='Lista de códigos de roles que reciben esta notificación'
    )
    
    # Control
    activo = models.BooleanField(default=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Notificación'
        verbose_name_plural = 'Tipos de Notificación'
        ordering = ['categoria', 'nombre']
        db_table = 'notif_tipo_notificacion'
        indexes = [
            models.Index(fields=['codigo', 'activo']),
            models.Index(fields=['categoria', 'prioridad_default']),
        ]
    
    def __str__(self):
        return f"{self.get_categoria_display()} - {self.nombre}"


# ============================================================================
# NOTIFICACIÓN (Núcleo del sistema)
# ============================================================================

class Notificacion(models.Model):
    """
    Registro individual de cada notificación enviada
    """
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de enviar'),
        ('ENVIADA', 'Enviada correctamente'),
        ('LEIDA', 'Leída por el usuario'),
        ('DESCARTADA', 'Descartada por el usuario'),
        ('ERROR', 'Error al enviar'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tipo y clasificación
    tipo_notificacion = models.ForeignKey(
        TipoNotificacion,
        on_delete=models.PROTECT,
        related_name='notificaciones'
    )
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='MEDIA',
        db_index=True
    )
    
    # Destinatario
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    
    # Contenido
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    datos_adicionales = models.JSONField(
        default=dict,
        blank=True,
        help_text='Datos extra en JSON (producto_id, quintal_id, etc)'
    )
    
    # ==========================================
    # RELACIÓN GENÉRICA (Clave para trazabilidad)
    # ==========================================
    # Permite relacionar la notificación con cualquier modelo
    # Ejemplos: Quintal, ProductoNormal, Venta, AlertaStock, etc
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='Tipo de objeto relacionado'
    )
    object_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='ID del objeto relacionado'
    )
    objeto_relacionado = GenericForeignKey('content_type', 'object_id')
    
    # URL de acción (si aplica)
    url_accion = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL para ver detalles o tomar acción'
    )
    
    # ==========================================
    # ESTADO Y CONTROL
    # ==========================================
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    requiere_accion = models.BooleanField(
        default=False,
        help_text='La notificación requiere acción del usuario'
    )
    accion_tomada = models.BooleanField(default=False)
    
    # ==========================================
    # CANALES DE ENVÍO
    # ==========================================
    enviada_web = models.BooleanField(default=False)
    enviada_email = models.BooleanField(default=False)
    enviada_push = models.BooleanField(default=False)
    enviada_sms = models.BooleanField(default=False)
    
    # ==========================================
    # FECHAS
    # ==========================================
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    fecha_expiracion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha después de la cual la notificación no es relevante'
    )
    
    # ==========================================
    # ERROR (si aplica)
    # ==========================================
    error_mensaje = models.TextField(blank=True)
    intentos_envio = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']
        db_table = 'notif_notificacion'
        indexes = [
            models.Index(fields=['usuario', '-fecha_creacion']),
            models.Index(fields=['estado', 'usuario']),
            models.Index(fields=['prioridad', '-fecha_creacion']),
            models.Index(fields=['tipo_notificacion', 'estado']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.get_icono_prioridad()} {self.titulo} - {self.usuario.get_full_name()}"
    
    def get_icono_prioridad(self):
        """Retorna icono según prioridad"""
        iconos = {
            'BAJA': 'ℹ️',
            'MEDIA': '⚠️',
            'ALTA': '🔥',
            'CRITICA': '🚨'
        }
        return iconos.get(self.prioridad, '⚠️')
    
    def marcar_leida(self):
        """Marca la notificación como leída"""
        if self.estado != 'LEIDA':
            self.estado = 'LEIDA'
            self.fecha_lectura = timezone.now()
            self.save()
    
    def marcar_descartada(self):
        """Marca la notificación como descartada"""
        self.estado = 'DESCARTADA'
        self.save()
    
    def marcar_accion_tomada(self):
        """Marca que se tomó acción sobre la notificación"""
        self.accion_tomada = True
        self.save()
    
    def esta_expirada(self):
        """Verifica si la notificación está expirada"""
        if not self.fecha_expiracion:
            return False
        return timezone.now() > self.fecha_expiracion
    
    def es_no_leida(self):
        """Verifica si está pendiente o enviada pero no leída"""
        return self.estado in ['PENDIENTE', 'ENVIADA']
    
    def puede_reenviar(self):
        """Verifica si se puede reintentar el envío"""
        return self.estado == 'ERROR' and self.intentos_envio < 3


# ============================================================================
# NOTIFICACIÓN PROGRAMADA
# ============================================================================

class NotificacionProgramada(models.Model):
    """
    Notificaciones programadas para envío futuro
    Ejemplo: Recordatorio de reorden de stock cada lunes
    """
    
    FRECUENCIA_CHOICES = [
        ('UNA_VEZ', 'Una sola vez'),
        ('DIARIA', 'Diaria'),
        ('SEMANAL', 'Semanal'),
        ('MENSUAL', 'Mensual'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Configuración
    tipo_notificacion = models.ForeignKey(
        TipoNotificacion,
        on_delete=models.CASCADE,
        related_name='notificaciones_programadas'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    
    # Programación
    frecuencia = models.CharField(
        max_length=20,
        choices=FRECUENCIA_CHOICES,
        default='UNA_VEZ'
    )
    fecha_proxima_ejecucion = models.DateTimeField(
        help_text='Próxima vez que se enviará la notificación'
    )
    hora_ejecucion = models.TimeField(
        null=True,
        blank=True,
        help_text='Hora del día para enviar (para notificaciones recurrentes)'
    )
    
    # Destinatarios
    usuarios = models.ManyToManyField(
        'authentication.Usuario',
        related_name='notificaciones_programadas',
        blank=True
    )
    roles = models.JSONField(
        default=list,
        blank=True,
        help_text='Enviar a usuarios con estos roles'
    )
    
    # Plantilla
    titulo_personalizado = models.CharField(max_length=200, blank=True)
    mensaje_personalizado = models.TextField(blank=True)
    
    # Control
    activa = models.BooleanField(default=True)
    
    # Historial
    ultima_ejecucion = models.DateTimeField(null=True, blank=True)
    total_ejecuciones = models.IntegerField(default=0)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='notificaciones_programadas_creadas'
    )
    
    class Meta:
        verbose_name = 'Notificación Programada'
        verbose_name_plural = 'Notificaciones Programadas'
        ordering = ['fecha_proxima_ejecucion']
        db_table = 'notif_programada'
    
    def __str__(self):
        return f"{self.nombre} ({self.get_frecuencia_display()})"


# ============================================================================
# PLANTILLA DE NOTIFICACIÓN
# ============================================================================

class PlantillaNotificacion(models.Model):
    """
    Plantillas reutilizables para notificaciones con variables
    """
    
    TIPO_PLANTILLA_CHOICES = [
        ('WEB', 'Notificación Web'),
        ('EMAIL', 'Email HTML'),
        ('SMS', 'Mensaje SMS'),
        ('PUSH', 'Push Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    # Tipo
    tipo_plantilla = models.CharField(
        max_length=20,
        choices=TIPO_PLANTILLA_CHOICES
    )
    
    # Contenido
    asunto = models.CharField(
        max_length=200,
        blank=True,
        help_text='Asunto del email o título de la notificación'
    )
    cuerpo = models.TextField(
        help_text='Contenido con variables: {{producto}}, {{cantidad}}, etc'
    )
    
    # Variables disponibles
    variables_disponibles = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de variables que se pueden usar: ["producto", "cantidad", "usuario"]'
    )
    
    # Control
    activa = models.BooleanField(default=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plantilla de Notificación'
        verbose_name_plural = 'Plantillas de Notificación'
        ordering = ['nombre']
        db_table = 'notif_plantilla'
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_plantilla_display()})"
    
    def renderizar(self, contexto):
        """
        Renderiza la plantilla con el contexto dado
        
        Args:
            contexto: dict con las variables a reemplazar
        
        Returns:
            str: Contenido renderizado
        """
        contenido = self.cuerpo
        for variable, valor in contexto.items():
            placeholder = f"{{{{{variable}}}}}"
            contenido = contenido.replace(placeholder, str(valor))
        return contenido


# ============================================================================
# LOG DE NOTIFICACIONES
# ============================================================================

class LogNotificacion(models.Model):
    """
    Registro de auditoría de todas las notificaciones enviadas
    """
    
    RESULTADO_CHOICES = [
        ('EXITOSO', 'Enviado exitosamente'),
        ('ERROR', 'Error al enviar'),
        ('RECHAZADO', 'Rechazado por el servidor'),
        ('REBOTADO', 'Email rebotado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación
    notificacion = models.ForeignKey(
        Notificacion,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Canal de envío
    canal = models.CharField(
        max_length=20,
        choices=[
            ('WEB', 'Web'),
            ('EMAIL', 'Email'),
            ('SMS', 'SMS'),
            ('PUSH', 'Push'),
        ]
    )
    
    # Resultado
    resultado = models.CharField(
        max_length=20,
        choices=RESULTADO_CHOICES
    )
    
    # Detalles
    destinatario = models.CharField(max_length=255)
    mensaje_error = models.TextField(blank=True)
    datos_respuesta = models.JSONField(
        default=dict,
        blank=True,
        help_text='Respuesta del servidor (ej: message_id de email)'
    )
    
    # Auditoría
    fecha_intento = models.DateTimeField(default=timezone.now)
    tiempo_respuesta = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text='Tiempo de respuesta en segundos'
    )
    
    class Meta:
        verbose_name = 'Log de Notificación'
        verbose_name_plural = 'Logs de Notificaciones'
        ordering = ['-fecha_intento']
        db_table = 'notif_log'
        indexes = [
            models.Index(fields=['notificacion', '-fecha_intento']),
            models.Index(fields=['canal', 'resultado']),
        ]
    
    def __str__(self):
        return f"{self.canal} - {self.resultado} - {self.fecha_intento.strftime('%d/%m/%Y %H:%M')}"


# ============================================================================
# PREFERENCIAS DE NOTIFICACIÓN POR USUARIO
# ============================================================================

class PreferenciasNotificacion(models.Model):
    """
    Preferencias individuales de cada usuario sobre notificaciones
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Usuario
    usuario = models.OneToOneField(
        'authentication.Usuario',
        on_delete=models.CASCADE,
        related_name='preferencias_notificaciones'
    )
    
    # ==========================================
    # CANALES
    # ==========================================
    recibir_notificaciones_web = models.BooleanField(default=True)
    recibir_notificaciones_email = models.BooleanField(default=True)
    recibir_notificaciones_push = models.BooleanField(default=False)
    recibir_notificaciones_sms = models.BooleanField(default=False)
    
    # ==========================================
    # POR CATEGORÍA
    # ==========================================
    notif_stock = models.BooleanField(default=True)
    notif_ventas = models.BooleanField(default=True)
    notif_financiero = models.BooleanField(default=True)
    notif_sistema = models.BooleanField(default=True)
    
    # ==========================================
    # CONFIGURACIÓN AVANZADA
    # ==========================================
    agrupar_notificaciones = models.BooleanField(
        default=True,
        help_text='Agrupar notificaciones similares'
    )
    solo_prioridad_alta = models.BooleanField(
        default=False,
        help_text='Recibir solo notificaciones de prioridad alta o crítica'
    )
    
    # Horario de no molestar
    no_molestar_activo = models.BooleanField(default=False)
    no_molestar_desde = models.TimeField(null=True, blank=True)
    no_molestar_hasta = models.TimeField(null=True, blank=True)
    
    # Auditoría
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Preferencias de Notificación'
        verbose_name_plural = 'Preferencias de Notificaciones'
        db_table = 'notif_preferencias'
    
    def __str__(self):
        return f"Preferencias de {self.usuario.get_full_name()}"
    
    def puede_recibir_notificacion(self, tipo_notificacion, prioridad='MEDIA'):
        """
        Verifica si el usuario puede recibir una notificación según sus preferencias
        """
        # Si solo quiere prioridad alta, verificar
        if self.solo_prioridad_alta and prioridad not in ['ALTA', 'CRITICA']:
            return False
        
        # Verificar horario de no molestar
        if self.no_molestar_activo and self.esta_en_horario_no_molestar():
            # Solo notificaciones críticas durante no molestar
            return prioridad == 'CRITICA'
        
        # Verificar categoría
        if tipo_notificacion.categoria == 'STOCK' and not self.notif_stock:
            return False
        if tipo_notificacion.categoria == 'VENTAS' and not self.notif_ventas:
            return False
        if tipo_notificacion.categoria == 'FINANCIERO' and not self.notif_financiero:
            return False
        if tipo_notificacion.categoria == 'SISTEMA' and not self.notif_sistema:
            return False
        
        return True
    
    def esta_en_horario_no_molestar(self):
        """Verifica si está en horario de no molestar"""
        if not self.no_molestar_activo or not self.no_molestar_desde or not self.no_molestar_hasta:
            return False
        
        hora_actual = timezone.now().time()
        return self.no_molestar_desde <= hora_actual <= self.no_molestar_hasta