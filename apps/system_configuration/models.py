# apps/system_configuration/models.py

"""
Sistema de Configuración Global de CommerceBox
Gestión centralizada de parámetros del sistema
"""

import uuid
import json
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


# ============================================================================
# CONFIGURACIÓN GLOBAL DEL SISTEMA (Singleton)
# ============================================================================

class ConfiguracionSistema(models.Model):
    """
    Configuración global única del sistema CommerceBox
    Patrón Singleton - Solo existe un registro
    """
    
    # ==========================================
    # INFORMACIÓN GENERAL
    # ==========================================
    nombre_empresa = models.CharField(
        max_length=200,
        default='CommerceBox',
        help_text='Nombre de la empresa/negocio'
    )
    ruc_empresa = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\d{10,20}$', 'RUC/NIT inválido')],
        help_text='RUC o NIT de la empresa'
    )
    direccion_empresa = models.TextField(
        blank=True,
        help_text='Dirección física del negocio'
    )
    telefono_empresa = models.CharField(
        max_length=20,
        blank=True,
        help_text='Teléfono principal'
    )
    email_empresa = models.EmailField(
        blank=True,
        help_text='Email de contacto'
    )
    sitio_web = models.URLField(
        blank=True,
        help_text='Sitio web de la empresa'
    )
    
    # ✅ NUEVO: Logo de la empresa
    logo_empresa = models.ImageField(
        upload_to='empresa/logos/',
        blank=True,
        null=True,
        help_text='Logo de la empresa (recomendado: 200x200px, formato PNG con fondo transparente)'
    )
    
    # ==========================================
    # CONFIGURACIÓN DE INVENTARIO
    # ==========================================
    prefijo_codigo_quintal = models.CharField(
        max_length=10,
        default='CBX-QNT',
        help_text='Prefijo para códigos de quintales'
    )
    prefijo_codigo_producto = models.CharField(
        max_length=10,
        default='CBX-PRD',
        help_text='Prefijo para códigos de productos'
    )
    longitud_codigo_secuencial = models.IntegerField(
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(10)],
        help_text='Longitud del número secuencial en códigos'
    )
    
    # Umbrales de stock
    umbral_stock_critico_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='% para considerar stock crítico (quintales)'
    )
    umbral_stock_bajo_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=25.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='% para considerar stock bajo (quintales)'
    )
    stock_minimo_default = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text='Stock mínimo por defecto para productos normales'
    )
    
    # Alertas de vencimiento
    dias_alerta_vencimiento = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text='Días antes del vencimiento para generar alerta'
    )
    peso_minimo_quintal_critico = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=5.000,
        help_text='Peso mínimo (kg) para considerar quintal crítico'
    )
    
    # ==========================================
    # CONFIGURACIÓN DE VENTAS
    # ==========================================
    prefijo_numero_factura = models.CharField(
        max_length=10,
        default='CBX',
        help_text='Prefijo para números de factura'
    )
    prefijo_numero_venta = models.CharField(
        max_length=10,
        default='VNT',
        help_text='Prefijo para números de venta'
    )
    iva_default = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='IVA por defecto (%)'
    )
    max_descuento_sin_autorizacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Descuento máximo sin autorización (%)'
    )
    permitir_ventas_credito = models.BooleanField(
        default=True,
        help_text='Permitir ventas a crédito'
    )
    dias_credito_default = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text='Días de crédito por defecto'
    )
    
    # ==========================================
    # CONFIGURACIÓN FINANCIERA
    # ==========================================
    moneda = models.CharField(
        max_length=3,
        default='USD',
        help_text='Código de moneda (USD, EUR, etc.)'
    )
    simbolo_moneda = models.CharField(
        max_length=5,
        default='$',
        help_text='Símbolo de la moneda'
    )
    decimales_moneda = models.IntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text='Número de decimales para montos'
    )
    
    # Caja
    monto_inicial_caja = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100.00,
        help_text='Monto inicial sugerido para apertura de caja'
    )
    monto_fondo_caja_chica = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
        help_text='Monto del fondo de caja chica'
    )
    alerta_diferencia_caja = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5.00,
        help_text='Diferencia máxima permitida en arqueo de caja'
    )
    
    # ==========================================
    # FACTURACIÓN ELECTRÓNICA
    # ==========================================
    facturacion_electronica_activa = models.BooleanField(
        default=False,
        help_text='Activar facturación electrónica'
    )
    ambiente_facturacion = models.CharField(
        max_length=20,
        choices=[
            ('PRUEBAS', 'Pruebas'),
            ('PRODUCCION', 'Producción'),
        ],
        default='PRUEBAS',
        help_text='Ambiente de facturación electrónica'
    )
    certificado_digital_path = models.CharField(
        max_length=500,
        blank=True,
        help_text='Ruta del certificado digital'
    )
    clave_certificado = models.CharField(
        max_length=200,
        blank=True,
        help_text='Clave del certificado (encriptada)'
    )
    
    # ==========================================
    # NOTIFICACIONES
    # ==========================================
    notificaciones_email_activas = models.BooleanField(
        default=True,
        help_text='Activar notificaciones por email'
    )
    email_notificaciones = models.EmailField(
        blank=True,
        help_text='Email principal para notificaciones'
    )
    emails_adicionales = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de emails adicionales'
    )
    notificar_stock_bajo = models.BooleanField(
        default=True,
        help_text='Notificar cuando hay stock bajo'
    )
    notificar_vencimientos = models.BooleanField(
        default=True,
        help_text='Notificar productos próximos a vencer'
    )
    notificar_cierre_caja = models.BooleanField(
        default=True,
        help_text='Notificar al cerrar caja'
    )
    
    # ==========================================
    # BACKUPS
    # ==========================================
    backup_automatico_activo = models.BooleanField(
        default=True,
        help_text='Activar backups automáticos'
    )
    frecuencia_backup = models.CharField(
        max_length=20,
        choices=[
            ('DIARIO', 'Diario'),
            ('SEMANAL', 'Semanal'),
            ('MENSUAL', 'Mensual'),
        ],
        default='DIARIO',
        help_text='Frecuencia de backups automáticos'
    )
    hora_backup = models.TimeField(
        default='02:00:00',
        help_text='Hora para ejecutar backup automático'
    )
    dias_retencion_backup = models.IntegerField(
        default=30,
        validators=[MinValueValidator(7), MaxValueValidator(365)],
        help_text='Días para mantener backups antiguos'
    )
    ruta_backup = models.CharField(
        max_length=500,
        default='/backups/',
        help_text='Ruta donde guardar backups'
    )
    
    # ==========================================
    # SISTEMA
    # ==========================================
    version_sistema = models.CharField(
        max_length=20,
        default='1.0.0',
        editable=False,
        help_text='Versión actual del sistema'
    )
    mantenimiento_activo = models.BooleanField(
        default=False,
        help_text='Modo mantenimiento (bloquea acceso)'
    )
    mensaje_mantenimiento = models.TextField(
        blank=True,
        default='Sistema en mantenimiento. Volveremos pronto.',
        help_text='Mensaje a mostrar durante mantenimiento'
    )
    
    # Logs
    activar_logs_detallados = models.BooleanField(
        default=True,
        help_text='Activar logs detallados del sistema'
    )
    dias_retencion_logs = models.IntegerField(
        default=90,
        validators=[MinValueValidator(7), MaxValueValidator(365)],
        help_text='Días para mantener logs'
    )
    
    # ==========================================
    # SEGURIDAD
    # ==========================================
    timeout_sesion = models.IntegerField(
        default=3600,
        validators=[MinValueValidator(300), MaxValueValidator(86400)],
        help_text='Tiempo de sesión en segundos (5 min - 24 hrs)'
    )
    intentos_login_maximos = models.IntegerField(
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(10)],
        help_text='Intentos de login antes de bloquear'
    )
    tiempo_bloqueo_cuenta = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(1440)],
        help_text='Minutos de bloqueo por intentos fallidos'
    )
    
    # ==========================================
    # INTERFAZ
    # ==========================================
    tema_interfaz = models.CharField(
        max_length=20,
        choices=[
            ('CLARO', 'Claro'),
            ('OSCURO', 'Oscuro'),
            ('AUTO', 'Automático'),
        ],
        default='CLARO',
        help_text='Tema visual de la interfaz'
    )
    idioma = models.CharField(
        max_length=5,
        default='es',
        choices=[
            ('es', 'Español'),
            ('en', 'English'),
        ],
        help_text='Idioma del sistema'
    )
    zona_horaria = models.CharField(
        max_length=50,
        default='America/Bogota',
        help_text='Zona horaria del sistema'
    )
    formato_fecha = models.CharField(
        max_length=20,
        default='DD/MM/YYYY',
        help_text='Formato de visualización de fechas'
    )
    formato_hora = models.CharField(
        max_length=20,
        default='24h',
        choices=[
            ('24h', '24 Horas'),
            ('12h', '12 Horas (AM/PM)'),
        ],
        help_text='Formato de visualización de hora'
    )
    
    # ==========================================
    # MÓDULOS ACTIVOS
    # ==========================================
    modulo_inventario_activo = models.BooleanField(
        default=True,
        help_text='Módulo de inventario activo'
    )
    modulo_ventas_activo = models.BooleanField(
        default=True,
        help_text='Módulo de ventas activo'
    )
    modulo_financiero_activo = models.BooleanField(
        default=True,
        help_text='Módulo financiero activo'
    )
    modulo_reportes_activo = models.BooleanField(
        default=True,
        help_text='Módulo de reportes activo'
    )
    modulo_alertas_activo = models.BooleanField(
        default=True,
        help_text='Sistema de alertas activo'
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
        related_name='configuraciones_sistema'
    )
    
    class Meta:
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuración del Sistema'
        db_table = 'sys_config_sistema'
    
    def __str__(self):
        return f"Configuración de {self.nombre_empresa}"
    
    def save(self, *args, **kwargs):
        """Asegurar que solo exista un registro (Singleton)"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevenir eliminación de la configuración"""
        pass
    
    @classmethod
    def get_config(cls):
        """Obtiene o crea la configuración única"""
        config, created = cls.objects.get_or_create(pk=1)
        return config
    
    def get_emails_notificacion(self):
        """Retorna lista completa de emails para notificaciones"""
        emails = []
        if self.email_notificaciones:
            emails.append(self.email_notificaciones)
        if self.emails_adicionales:
            emails.extend(self.emails_adicionales)
        return emails


# ============================================================================
# REGISTRO DE BACKUPS
# ============================================================================

class RegistroBackup(models.Model):
    """
    Registro de backups realizados
    """
    
    TIPO_BACKUP_CHOICES = [
        ('COMPLETO', 'Backup Completo'),
        ('INCREMENTAL', 'Backup Incremental'),
        ('MANUAL', 'Backup Manual'),
    ]
    
    ESTADO_CHOICES = [
        ('EXITOSO', '✅ Exitoso'),
        ('FALLIDO', '❌ Fallido'),
        ('EN_PROCESO', '⏳ En Proceso'),
        ('CANCELADO', '⚠️ Cancelado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información del backup
    nombre_archivo = models.CharField(
        max_length=200,
        help_text='Nombre del archivo de backup'
    )
    ruta_archivo = models.CharField(
        max_length=500,
        help_text='Ruta completa del backup'
    )
    tipo_backup = models.CharField(
        max_length=20,
        choices=TIPO_BACKUP_CHOICES
    )
    
    # Tamaño y contenido
    tamaño_bytes = models.BigIntegerField(
        default=0,
        help_text='Tamaño del backup en bytes'
    )
    tamaño_comprimido_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Tamaño comprimido del backup'
    )
    
    # Tablas incluidas
    tablas_incluidas = models.JSONField(
        default=list,
        help_text='Lista de tablas incluidas en el backup'
    )
    total_registros = models.BigIntegerField(
        default=0,
        help_text='Total de registros respaldados'
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='EN_PROCESO',
        db_index=True
    )
    mensaje_error = models.TextField(
        blank=True,
        help_text='Mensaje de error si falló'
    )
    
    # Tiempos
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duración del backup en segundos'
    )
    
    # Usuario
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Usuario que ejecutó el backup'
    )
    
    # Restauración
    restaurado = models.BooleanField(
        default=False,
        help_text='Indica si este backup fue restaurado'
    )
    fecha_restauracion = models.DateTimeField(
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Registro de Backup'
        verbose_name_plural = 'Registros de Backups'
        ordering = ['-fecha_inicio']
        db_table = 'sys_config_backup'
        indexes = [
            models.Index(fields=['-fecha_inicio', 'estado']),
            models.Index(fields=['tipo_backup', 'estado']),
        ]
    
    def __str__(self):
        return f"{self.nombre_archivo} - {self.get_estado_display()}"
    
    def get_tamaño_legible(self):
        """Retorna el tamaño en formato legible"""
        if self.tamaño_bytes < 1024:
            return f"{self.tamaño_bytes} B"
        elif self.tamaño_bytes < 1024**2:
            return f"{self.tamaño_bytes / 1024:.2f} KB"
        elif self.tamaño_bytes < 1024**3:
            return f"{self.tamaño_bytes / (1024**2):.2f} MB"
        else:
            return f"{self.tamaño_bytes / (1024**3):.2f} GB"
    
    def marcar_completado(self, duracion=None):
        """Marca el backup como completado"""
        self.estado = 'EXITOSO'
        self.fecha_finalizacion = timezone.now()
        if duracion:
            self.duracion_segundos = duracion
        else:
            self.duracion_segundos = int(
                (self.fecha_finalizacion - self.fecha_inicio).total_seconds()
            )
        self.save()
    
    def marcar_fallido(self, mensaje_error):
        """Marca el backup como fallido"""
        self.estado = 'FALLIDO'
        self.mensaje_error = mensaje_error
        self.fecha_finalizacion = timezone.now()
        self.save()


# ============================================================================
# PARÁMETROS CONFIGURABLES POR MÓDULO
# ============================================================================

class ParametroSistema(models.Model):
    """
    Parámetros configurables adicionales del sistema
    Permite extensibilidad sin modificar el modelo principal
    """
    
    TIPO_DATO_CHOICES = [
        ('STRING', 'Texto'),
        ('INTEGER', 'Número Entero'),
        ('DECIMAL', 'Número Decimal'),
        ('BOOLEAN', 'Verdadero/Falso'),
        ('JSON', 'JSON/Objeto'),
        ('DATE', 'Fecha'),
        ('DATETIME', 'Fecha y Hora'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    modulo = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Módulo al que pertenece (inventory, sales, etc.)'
    )
    clave = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Clave única del parámetro'
    )
    nombre = models.CharField(
        max_length=200,
        help_text='Nombre descriptivo del parámetro'
    )
    descripcion = models.TextField(
        blank=True,
        help_text='Descripción detallada del parámetro'
    )
    
    # Tipo y valor
    tipo_dato = models.CharField(
        max_length=20,
        choices=TIPO_DATO_CHOICES
    )
    valor = models.TextField(
        help_text='Valor del parámetro (almacenado como texto)'
    )
    valor_default = models.TextField(
        help_text='Valor por defecto'
    )
    
    # Validación
    requerido = models.BooleanField(
        default=False,
        help_text='Parámetro obligatorio'
    )
    editable = models.BooleanField(
        default=True,
        help_text='Puede ser editado por usuarios'
    )
    validacion_regex = models.CharField(
        max_length=200,
        blank=True,
        help_text='Expresión regular para validación'
    )
    
    # Orden y grupo
    grupo = models.CharField(
        max_length=100,
        blank=True,
        help_text='Grupo para organizar parámetros'
    )
    orden = models.IntegerField(
        default=0,
        help_text='Orden de visualización'
    )
    
    # Estado
    activo = models.BooleanField(default=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Parámetro del Sistema'
        verbose_name_plural = 'Parámetros del Sistema'
        unique_together = [['modulo', 'clave']]
        ordering = ['modulo', 'grupo', 'orden', 'nombre']
        db_table = 'sys_config_parametro'
        indexes = [
            models.Index(fields=['modulo', 'activo']),
            models.Index(fields=['clave']),
        ]
    
    def __str__(self):
        return f"{self.modulo}.{self.clave}"
    
    def get_valor_typed(self):
        """Retorna el valor convertido al tipo correcto"""
        if self.tipo_dato == 'INTEGER':
            return int(self.valor)
        elif self.tipo_dato == 'DECIMAL':
            return Decimal(self.valor)
        elif self.tipo_dato == 'BOOLEAN':
            return self.valor.lower() in ['true', '1', 'yes', 'si']
        elif self.tipo_dato == 'JSON':
            return json.loads(self.valor)
        elif self.tipo_dato == 'DATE':
            from django.utils.dateparse import parse_date
            return parse_date(self.valor)
        elif self.tipo_dato == 'DATETIME':
            from django.utils.dateparse import parse_datetime
            return parse_datetime(self.valor)
        else:
            return self.valor
    
    def set_valor_typed(self, valor):
        """Establece el valor desde un tipo Python"""
        if self.tipo_dato == 'JSON':
            self.valor = json.dumps(valor)
        elif self.tipo_dato in ['DATE', 'DATETIME']:
            self.valor = valor.isoformat()
        else:
            self.valor = str(valor)


# ============================================================================
# LOG DE CAMBIOS DE CONFIGURACIÓN
# ============================================================================

class LogConfiguracion(models.Model):
    """
    Auditoría de cambios en la configuración del sistema
    """
    
    TIPO_CAMBIO_CHOICES = [
        ('CREACION', 'Creación'),
        ('MODIFICACION', 'Modificación'),
        ('ELIMINACION', 'Eliminación'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Qué se cambió
    tabla = models.CharField(
        max_length=100,
        help_text='Tabla que se modificó'
    )
    registro_id = models.CharField(
        max_length=50,
        help_text='ID del registro modificado'
    )
    tipo_cambio = models.CharField(
        max_length=20,
        choices=TIPO_CAMBIO_CHOICES
    )
    
    # Detalles del cambio
    campo_modificado = models.CharField(
        max_length=100,
        blank=True,
        help_text='Campo específico modificado'
    )
    valor_anterior = models.TextField(
        blank=True,
        help_text='Valor antes del cambio'
    )
    valor_nuevo = models.TextField(
        blank=True,
        help_text='Valor después del cambio'
    )
    
    # Contexto
    descripcion = models.TextField(
        blank=True,
        help_text='Descripción del cambio'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    # Usuario
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Fecha
    fecha_cambio = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        verbose_name = 'Log de Configuración'
        verbose_name_plural = 'Logs de Configuración'
        ordering = ['-fecha_cambio']
        db_table = 'sys_config_log'
        indexes = [
            models.Index(fields=['-fecha_cambio']),
            models.Index(fields=['tabla', '-fecha_cambio']),
            models.Index(fields=['usuario', '-fecha_cambio']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.tabla} - {self.fecha_cambio}"


# ============================================================================
# HEALTH CHECK DEL SISTEMA
# ============================================================================

class HealthCheck(models.Model):
    """
    Registro de health checks del sistema
    """
    
    ESTADO_CHOICES = [
        ('SALUDABLE', '✅ Saludable'),
        ('ADVERTENCIA', '⚠️ Advertencia'),
        ('CRITICO', '🔴 Crítico'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Estado general
    estado_general = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES
    )
    
    # Componentes
    base_datos_ok = models.BooleanField(default=True)
    redis_ok = models.BooleanField(default=True)
    celery_ok = models.BooleanField(default=True)
    disco_ok = models.BooleanField(default=True)
    memoria_ok = models.BooleanField(default=True)
    
    # Métricas
    espacio_disco_libre_gb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    uso_memoria_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    tiempo_respuesta_db_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Tiempo de respuesta de la base de datos en ms'
    )
    
    # Detalles
    detalles = models.JSONField(
        default=dict,
        help_text='Detalles adicionales del health check'
    )
    errores = models.JSONField(
        default=list,
        help_text='Lista de errores encontrados'
    )
    advertencias = models.JSONField(
        default=list,
        help_text='Lista de advertencias'
    )
    
    # Fecha
    fecha_check = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        verbose_name = 'Health Check'
        verbose_name_plural = 'Health Checks'
        ordering = ['-fecha_check']
        db_table = 'sys_config_health_check'
    
    def __str__(self):
        return f"Health Check - {self.get_estado_general_display()} - {self.fecha_check}"


# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def get_parametro(modulo, clave, default=None):
    """
    Obtiene el valor de un parámetro del sistema
    
    Usage:
        valor = get_parametro('inventory', 'dias_alerta_vencimiento', default=30)
    """
    try:
        param = ParametroSistema.objects.get(
            modulo=modulo,
            clave=clave,
            activo=True
        )
        return param.get_valor_typed()
    except ParametroSistema.DoesNotExist:
        return default


def set_parametro(modulo, clave, valor, usuario=None):
    """
    Establece el valor de un parámetro del sistema
    
    Usage:
        set_parametro('inventory', 'dias_alerta_vencimiento', 45, usuario=request.user)
    """
    try:
        param = ParametroSistema.objects.get(modulo=modulo, clave=clave)
        valor_anterior = param.valor
        param.set_valor_typed(valor)
        param.actualizado_por = usuario
        param.save()
        
        # Registrar cambio en log
        LogConfiguracion.objects.create(
            tabla='ParametroSistema',
            registro_id=str(param.id),
            tipo_cambio='MODIFICACION',
            campo_modificado='valor',
            valor_anterior=valor_anterior,
            valor_nuevo=param.valor,
            usuario=usuario,
            descripcion=f"Cambio de parámetro {modulo}.{clave}"
        )
        
        return True
    except ParametroSistema.DoesNotExist:
        return False


# ============================================================================
# FUNCIONES HELPER PARA SALES (IVA)
# ============================================================================

def get_iva_default():
    """
    Obtiene el IVA por defecto configurado en el sistema
    
    Returns:
        Decimal: Porcentaje de IVA (ej: Decimal('15.00'))
    
    Usage en sales:
        from apps.system_configuration.models import get_iva_default
        
        iva_porcentaje = get_iva_default()  # Ej: 15.00
        monto_iva = subtotal * (iva_porcentaje / 100)
    """
    config = ConfiguracionSistema.get_config()
    return config.iva_default


def calcular_iva(subtotal):
    """
    Calcula el monto de IVA sobre un subtotal
    
    Args:
        subtotal (Decimal): Monto base sin IVA
    
    Returns:
        Decimal: Monto del IVA calculado
    
    Usage:
        from apps.system_configuration.models import calcular_iva
        
        subtotal = Decimal('100.00')
        iva = calcular_iva(subtotal)  # Retorna 15.00 si IVA está en 15%
    """
    iva_porcentaje = get_iva_default()
    return subtotal * (iva_porcentaje / Decimal('100'))