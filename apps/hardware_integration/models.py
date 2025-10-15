# apps/hardware_integration/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import json


# ============================================================================
# CONFIGURACIÓN DE IMPRESORAS
# ============================================================================

class Impresora(models.Model):
    """
    Registro y configuración de impresoras del sistema
    Soporta diferentes tipos y métodos de conexión
    """
    
    TIPO_IMPRESORA_CHOICES = [
        ('TERMICA_TICKET', 'Térmica de Tickets (80mm)'),
        ('TERMICA_FACTURA', 'Térmica de Facturas (80mm con gaveta)'),
        ('ETIQUETAS', 'Etiquetas/Códigos de Barras'),
        ('LASER', 'Láser/Tinta (A4)'),
        ('MATRIZ', 'Matriz de Puntos'),
    ]
    
    TIPO_CONEXION_CHOICES = [
        ('USB', 'USB Directo'),
        ('LAN', 'Red LAN (Ethernet)'),
        ('WIFI', 'WiFi'),
        ('SERIAL', 'Puerto Serial (COM)'),
        ('PARALELO', 'Puerto Paralelo (LPT)'),
        ('DRIVER', 'Driver del Sistema'),
        ('RAW', 'Raw Socket TCP/IP'),
    ]
    
    PROTOCOLO_CHOICES = [
        ('ESC_POS', 'ESC/POS (Epson Standard)'),
        ('STAR', 'Star Line Mode'),
        ('ZPL', 'ZPL (Zebra)'),
        ('EPL', 'EPL (Eltron)'),
        ('TSPL', 'TSPL (TSC)'),
        ('DPL', 'DPL (Datamax)'),
        ('CUSTOM', 'Personalizado'),
        ('WINDOWS', 'Windows Driver'),
    ]
    
    ESTADO_CHOICES = [
        ('ACTIVA', '🟢 Activa y Funcionando'),
        ('INACTIVA', '🟡 Inactiva'),
        ('ERROR', '🔴 Con Error'),
        ('MANTENIMIENTO', '🔧 En Mantenimiento'),
    ]
    
    # Identificación
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código interno (ej: IMP-001)"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo de la impresora"
    )
    
    # Información del dispositivo
    marca = models.CharField(
        max_length=50,
        help_text="Marca de la impresora (Epson, Star, Zebra, etc)"
    )
    modelo = models.CharField(
        max_length=50,
        help_text="Modelo específico (ej: TM-T20III, ZD220, etc)"
    )
    numero_serie = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de serie del dispositivo"
    )
    
    # Tipo y conexión
    tipo_impresora = models.CharField(
        max_length=20,
        choices=TIPO_IMPRESORA_CHOICES
    )
    tipo_conexion = models.CharField(
        max_length=20,
        choices=TIPO_CONEXION_CHOICES
    )
    protocolo = models.CharField(
        max_length=20,
        choices=PROTOCOLO_CHOICES,
        default='ESC_POS'
    )
    
    # Configuración de conexión
    # USB
    puerto_usb = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ruta del dispositivo USB (ej: /dev/usb/lp0, COM3)"
    )
    vid_usb = models.CharField(
        max_length=10,
        blank=True,
        help_text="Vendor ID USB (hexadecimal)"
    )
    pid_usb = models.CharField(
        max_length=10,
        blank=True,
        help_text="Product ID USB (hexadecimal)"
    )
    
    # Red (LAN/WiFi)
    direccion_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP de la impresora"
    )
    puerto_red = models.IntegerField(
        null=True,
        blank=True,
        default=9100,
        help_text="Puerto de red (normalmente 9100)"
    )
    mac_address = models.CharField(
        max_length=20,
        blank=True,
        help_text="Dirección MAC de la impresora"
    )
    
    # Serial
    puerto_serial = models.CharField(
        max_length=20,
        blank=True,
        help_text="Puerto serial (COM1, /dev/ttyS0, etc)"
    )
    baudrate = models.IntegerField(
        null=True,
        blank=True,
        default=9600,
        help_text="Velocidad del puerto serial"
    )
    
    # Driver del sistema
    nombre_driver = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre del driver instalado en Windows/CUPS"
    )
    
    # Configuración de papel (para tickets y etiquetas)
    ancho_papel = models.IntegerField(
        default=80,
        validators=[MinValueValidator(20), MaxValueValidator(300)],
        help_text="Ancho del papel en mm"
    )
    largo_maximo = models.IntegerField(
        null=True,
        blank=True,
        help_text="Largo máximo del papel en mm (null = continuo)"
    )
    
    # Para etiquetas
    ancho_etiqueta = models.IntegerField(
        null=True,
        blank=True,
        help_text="Ancho de la etiqueta en mm"
    )
    alto_etiqueta = models.IntegerField(
        null=True,
        blank=True,
        help_text="Alto de la etiqueta en mm"
    )
    gap_etiquetas = models.IntegerField(
        null=True,
        blank=True,
        default=3,
        help_text="Espacio entre etiquetas en mm"
    )
    
    # Configuración de impresión
    densidad_impresion = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Densidad/Oscuridad de impresión (1-5)"
    )
    velocidad_impresion = models.IntegerField(
        default=100,
        validators=[MinValueValidator(50), MaxValueValidator(300)],
        help_text="Velocidad de impresión en mm/s"
    )
    
    # Capacidades
    soporta_corte_automatico = models.BooleanField(
        default=True,
        help_text="La impresora tiene cortador automático"
    )
    soporta_corte_parcial = models.BooleanField(
        default=True,
        help_text="Soporta corte parcial del papel"
    )
    soporta_codigo_barras = models.BooleanField(
        default=True,
        help_text="Puede imprimir códigos de barras nativamente"
    )
    soporta_qr = models.BooleanField(
        default=False,
        help_text="Puede imprimir códigos QR nativamente"
    )
    soporta_imagenes = models.BooleanField(
        default=False,
        help_text="Puede imprimir imágenes/logos"
    )
    
    # Gaveta de dinero (para impresoras de tickets)
    tiene_gaveta = models.BooleanField(
        default=False,
        help_text="Tiene gaveta de dinero conectada"
    )
    pin_gaveta = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Pin de la gaveta (0 o 1)"
    )
    
    # Estado y ubicación
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='ACTIVA'
    )
    ubicacion = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ubicación física (ej: Caja 1, Bodega, etc)"
    )
    
    # Configuración adicional (JSON)
    configuracion_extra = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuración adicional específica del modelo"
    )
    
    # Uso predeterminado
    es_principal_tickets = models.BooleanField(
        default=False,
        help_text="Es la impresora principal para tickets"
    )
    es_principal_facturas = models.BooleanField(
        default=False,
        help_text="Es la impresora principal para facturas"
    )
    es_principal_etiquetas = models.BooleanField(
        default=False,
        help_text="Es la impresora principal para etiquetas"
    )
    
    # Auditoría
    fecha_instalacion = models.DateTimeField(default=timezone.now)
    fecha_ultima_prueba = models.DateTimeField(null=True, blank=True)
    fecha_ultimo_mantenimiento = models.DateTimeField(null=True, blank=True)
    contador_impresiones = models.BigIntegerField(
        default=0,
        help_text="Contador total de impresiones realizadas"
    )
    
    # Notas
    notas = models.TextField(
        blank=True,
        help_text="Notas sobre configuración, problemas, etc"
    )
    
    class Meta:
        verbose_name = 'Impresora'
        verbose_name_plural = 'Impresoras'
        ordering = ['ubicacion', 'nombre']
        db_table = 'hw_impresora'
        indexes = [
            models.Index(fields=['tipo_impresora', 'estado']),
            models.Index(fields=['es_principal_tickets']),
            models.Index(fields=['es_principal_facturas']),
            models.Index(fields=['es_principal_etiquetas']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.marca} {self.modelo}) - {self.ubicacion}"
    
    def clean(self):
        """Validación del modelo"""
        # Validar que tenga configuración según tipo de conexión
        if self.tipo_conexion == 'USB' and not self.puerto_usb:
            raise ValidationError('Para conexión USB debe especificar el puerto USB')
        
        if self.tipo_conexion in ['LAN', 'WIFI'] and not self.direccion_ip:
            raise ValidationError('Para conexión de red debe especificar la dirección IP')
        
        if self.tipo_conexion == 'SERIAL' and not self.puerto_serial:
            raise ValidationError('Para conexión serial debe especificar el puerto')
        
        if self.tipo_conexion == 'DRIVER' and not self.nombre_driver:
            raise ValidationError('Para conexión por driver debe especificar el nombre del driver')
        
        # Validar configuración de etiquetas
        if self.tipo_impresora == 'ETIQUETAS':
            if not self.ancho_etiqueta or not self.alto_etiqueta:
                raise ValidationError('Para impresoras de etiquetas debe especificar ancho y alto')
    
    def get_connection_info(self):
        """Retorna información de conexión formateada"""
        if self.tipo_conexion == 'USB':
            return f"USB: {self.puerto_usb}"
        elif self.tipo_conexion in ['LAN', 'WIFI']:
            return f"{self.tipo_conexion}: {self.direccion_ip}:{self.puerto_red}"
        elif self.tipo_conexion == 'SERIAL':
            return f"Serial: {self.puerto_serial} @ {self.baudrate}"
        elif self.tipo_conexion == 'DRIVER':
            return f"Driver: {self.nombre_driver}"
        return self.tipo_conexion
    
    def incrementar_contador(self):
        """Incrementa el contador de impresiones"""
        self.contador_impresiones += 1
        self.save(update_fields=['contador_impresiones'])


# ============================================================================
# PLANTILLAS DE IMPRESIÓN
# ============================================================================

class PlantillaImpresion(models.Model):
    """
    Plantillas personalizables para diferentes tipos de documentos
    """
    
    TIPO_DOCUMENTO_CHOICES = [
        ('TICKET', 'Ticket de Venta'),
        ('FACTURA', 'Factura'),
        ('ETIQUETA_PRODUCTO', 'Etiqueta de Producto'),
        ('ETIQUETA_PRECIO', 'Etiqueta de Precio'),
        ('CODIGO_BARRAS', 'Código de Barras Simple'),
        ('REPORTE_Z', 'Reporte Z (Cierre de Caja)'),
        ('VALE', 'Vale/Comprobante'),
    ]
    
    FORMATO_CHOICES = [
        ('TEXTO', 'Texto Plano'),
        ('HTML', 'HTML'),
        ('ESC_POS', 'Comandos ESC/POS'),
        ('ZPL', 'ZPL (Zebra)'),
        ('TSPL', 'TSPL (TSC)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único de la plantilla"
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    # Tipo y formato
    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES
    )
    formato = models.CharField(
        max_length=20,
        choices=FORMATO_CHOICES,
        default='TEXTO'
    )
    
    # Impresora asociada (opcional)
    impresora = models.ForeignKey(
        Impresora,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plantillas',
        help_text="Impresora específica para esta plantilla"
    )
    
    # Contenido de la plantilla
    contenido = models.TextField(
        help_text="Contenido de la plantilla con variables"
    )
    
    # Variables disponibles (JSON)
    variables_disponibles = models.JSONField(
        default=list,
        help_text="Lista de variables disponibles para esta plantilla"
    )
    
    # Configuración de diseño
    incluir_logo = models.BooleanField(default=True)
    incluir_encabezado = models.BooleanField(default=True)
    incluir_pie = models.BooleanField(default=True)
    
    # Márgenes (en mm)
    margen_superior = models.IntegerField(default=5)
    margen_inferior = models.IntegerField(default=5)
    margen_izquierdo = models.IntegerField(default=5)
    margen_derecho = models.IntegerField(default=5)
    
    # Estado
    activa = models.BooleanField(default=True)
    es_predeterminada = models.BooleanField(
        default=False,
        help_text="Es la plantilla predeterminada para este tipo"
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plantilla de Impresión'
        verbose_name_plural = 'Plantillas de Impresión'
        ordering = ['tipo_documento', 'nombre']
        db_table = 'hw_plantilla_impresion'
        unique_together = [['tipo_documento', 'es_predeterminada']]
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_documento_display()})"


# ============================================================================
# CONFIGURACIÓN DE CÓDIGOS DE BARRAS
# ============================================================================

class ConfiguracionCodigoBarras(models.Model):
    """
    Configuración para generación de códigos de barras y etiquetas
    """
    
    TIPO_CODIGO_CHOICES = [
        ('EAN13', 'EAN-13'),
        ('EAN8', 'EAN-8'),
        ('UPC', 'UPC-A'),
        ('CODE128', 'Code 128'),
        ('CODE39', 'Code 39'),
        ('QR', 'Código QR'),
        ('DATAMATRIX', 'Data Matrix'),
        ('PDF417', 'PDF417'),
    ]
    
    POSICION_TEXTO_CHOICES = [
        ('ARRIBA', 'Arriba del código'),
        ('ABAJO', 'Abajo del código'),
        ('NINGUNO', 'Sin texto'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre de la configuración"
    )
    
    # Tipo de código
    tipo_codigo = models.CharField(
        max_length=20,
        choices=TIPO_CODIGO_CHOICES,
        default='CODE128'
    )
    
    # Prefijo y sufijo
    prefijo = models.CharField(
        max_length=10,
        blank=True,
        help_text="Prefijo para el código (ej: CBX)"
    )
    sufijo = models.CharField(
        max_length=10,
        blank=True,
        help_text="Sufijo para el código"
    )
    longitud_secuencia = models.IntegerField(
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(10)],
        help_text="Longitud del número secuencial"
    )
    ultimo_numero = models.BigIntegerField(
        default=0,
        help_text="Último número generado"
    )
    
    # Diseño del código
    ancho_codigo = models.IntegerField(
        default=50,
        validators=[MinValueValidator(20), MaxValueValidator(200)],
        help_text="Ancho del código en mm"
    )
    alto_codigo = models.IntegerField(
        default=15,
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        help_text="Alto del código en mm"
    )
    
    # Texto
    mostrar_texto = models.BooleanField(
        default=True,
        help_text="Mostrar el texto del código"
    )
    posicion_texto = models.CharField(
        max_length=10,
        choices=POSICION_TEXTO_CHOICES,
        default='ABAJO'
    )
    tamaño_fuente = models.IntegerField(
        default=10,
        validators=[MinValueValidator(6), MaxValueValidator(20)]
    )
    
    # Configuración de etiqueta
    incluir_nombre_producto = models.BooleanField(default=True)
    incluir_precio = models.BooleanField(default=True)
    incluir_fecha = models.BooleanField(default=False)
    incluir_marca = models.BooleanField(default=False)
    
    # Para productos
    es_para_productos = models.BooleanField(default=True)
    es_para_quintales = models.BooleanField(default=True)
    
    # Estado
    activa = models.BooleanField(default=True)
    es_predeterminada = models.BooleanField(default=False)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de Código de Barras'
        verbose_name_plural = 'Configuraciones de Códigos de Barras'
        ordering = ['nombre']
        db_table = 'hw_config_codigo_barras'
    
    def __str__(self):
        return f"{self.nombre} ({self.tipo_codigo})"
    
    def generar_siguiente_codigo(self):
        """Genera el siguiente código en la secuencia"""
        self.ultimo_numero += 1
        numero = str(self.ultimo_numero).zfill(self.longitud_secuencia)
        codigo = f"{self.prefijo}{numero}{self.sufijo}"
        self.save(update_fields=['ultimo_numero'])
        return codigo


# ============================================================================
# GAVETA DE DINERO
# ============================================================================

class GavetaDinero(models.Model):
    """
    Configuración de gavetas de dinero
    """
    
    TIPO_CONEXION_CHOICES = [
        ('IMPRESORA', 'Conectada a Impresora'),
        ('USB', 'USB Directo'),
        ('SERIAL', 'Puerto Serial'),
        ('RJ11', 'RJ11/RJ12'),
    ]
    
    ESTADO_CHOICES = [
        ('CERRADA', '🔒 Cerrada'),
        ('ABIERTA', '🔓 Abierta'),
        ('DESCONECTADA', '⚠️ Desconectada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código interno (ej: GAV-001)"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo"
    )
    
    # Conexión
    tipo_conexion = models.CharField(
        max_length=20,
        choices=TIPO_CONEXION_CHOICES,
        default='IMPRESORA'
    )
    
    # Si está conectada a impresora
    impresora = models.ForeignKey(
        Impresora,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gavetas'
    )
    
    # Para conexión directa
    puerto = models.CharField(
        max_length=50,
        blank=True,
        help_text="Puerto de conexión directa"
    )
    
    # Configuración de apertura
    comando_apertura = models.CharField(
        max_length=100,
        blank=True,
        default='\\x1b\\x70\\x00\\x19\\xfa',
        help_text="Comando ESC/POS para abrir (hexadecimal)"
    )
    duracion_pulso = models.IntegerField(
        default=100,
        help_text="Duración del pulso en ms"
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='CERRADA'
    )
    ubicacion = models.CharField(
        max_length=100,
        help_text="Ubicación física (ej: Caja 1)"
    )
    
    # Control
    activa = models.BooleanField(default=True)
    abrir_en_venta = models.BooleanField(
        default=True,
        help_text="Abrir automáticamente al completar venta"
    )
    abrir_en_cobro = models.BooleanField(
        default=True,
        help_text="Abrir al registrar cobro"
    )
    
    # Seguridad
    requiere_autorizacion = models.BooleanField(
        default=False,
        help_text="Requiere autorización para apertura manual"
    )
    
    # Auditoría
    contador_aperturas = models.BigIntegerField(default=0)
    fecha_ultima_apertura = models.DateTimeField(null=True, blank=True)
    usuario_ultima_apertura = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Notas
    notas = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Gaveta de Dinero'
        verbose_name_plural = 'Gavetas de Dinero'
        ordering = ['ubicacion', 'nombre']
        db_table = 'hw_gaveta_dinero'
    
    def __str__(self):
        return f"{self.nombre} - {self.ubicacion}"


# ============================================================================
# REGISTRO DE IMPRESIONES
# ============================================================================

class RegistroImpresion(models.Model):
    """
    Log de todas las impresiones realizadas
    """
    
    TIPO_DOCUMENTO_CHOICES = [
        ('TICKET', 'Ticket de Venta'),
        ('FACTURA', 'Factura'),
        ('ETIQUETA', 'Etiqueta'),
        ('CODIGO_BARRAS', 'Código de Barras'),
        ('REPORTE', 'Reporte'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('EXITOSO', '✅ Exitoso'),
        ('ERROR', '❌ Error'),
        ('CANCELADO', '⚠️ Cancelado'),
        ('REINTENTANDO', '🔄 Reintentando'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Impresora utilizada
    impresora = models.ForeignKey(
        Impresora,
        on_delete=models.SET_NULL,
        null=True,
        related_name='impresiones'
    )
    
    # Tipo de documento
    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES
    )
    
    # Referencias
    venta = models.ForeignKey(
        'sales_management.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    producto = models.ForeignKey(
        'inventory_management.Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Detalles
    numero_documento = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número del documento impreso"
    )
    contenido_resumen = models.TextField(
        blank=True,
        help_text="Resumen del contenido impreso"
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES
    )
    mensaje_error = models.TextField(
        blank=True,
        help_text="Mensaje de error si falló"
    )
    intentos = models.IntegerField(
        default=1,
        help_text="Número de intentos realizados"
    )
    
    # Auditoría
    fecha_impresion = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Métricas
    tiempo_procesamiento = models.IntegerField(
        null=True,
        blank=True,
        help_text="Tiempo de procesamiento en ms"
    )
    tamaño_bytes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Tamaño del documento en bytes"
    )
    
    class Meta:
        verbose_name = 'Registro de Impresión'
        verbose_name_plural = 'Registros de Impresión'
        ordering = ['-fecha_impresion']
        db_table = 'hw_registro_impresion'
        indexes = [
            models.Index(fields=['-fecha_impresion']),
            models.Index(fields=['impresora', '-fecha_impresion']),
            models.Index(fields=['tipo_documento', 'estado']),
        ]
    
    def __str__(self):
        return f"{self.tipo_documento} - {self.fecha_impresion} - {self.estado}"


# ============================================================================
# CONFIGURACIÓN DE ESCÁNER
# ============================================================================

class EscanerCodigoBarras(models.Model):
    """
    Configuración de escáneres de códigos de barras
    """
    
    TIPO_ESCANER_CHOICES = [
        ('USB_HID', 'USB HID (Teclado)'),
        ('USB_SERIAL', 'USB Serial'),
        ('BLUETOOTH', 'Bluetooth'),
        ('WIFI', 'WiFi'),
    ]
    
    MODO_OPERACION_CHOICES = [
        ('MANUAL', 'Manual (Gatillo)'),
        ('AUTOMATICO', 'Automático (Presentación)'),
        ('CONTINUO', 'Continuo'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    numero_serie = models.CharField(max_length=100, blank=True)
    
    # Tipo y conexión
    tipo_escaner = models.CharField(
        max_length=20,
        choices=TIPO_ESCANER_CHOICES,
        default='USB_HID'
    )
    modo_operacion = models.CharField(
        max_length=20,
        choices=MODO_OPERACION_CHOICES,
        default='MANUAL'
    )
    
    # Configuración
    prefijo = models.CharField(
        max_length=10,
        blank=True,
        help_text="Prefijo a agregar a las lecturas"
    )
    sufijo = models.CharField(
        max_length=10,
        blank=True,
        default='\\r\\n',
        help_text="Sufijo (normalmente Enter)"
    )
    
    # Tipos de código soportados
    soporta_ean13 = models.BooleanField(default=True)
    soporta_ean8 = models.BooleanField(default=True)
    soporta_upc = models.BooleanField(default=True)
    soporta_code128 = models.BooleanField(default=True)
    soporta_code39 = models.BooleanField(default=True)
    soporta_qr = models.BooleanField(default=False)
    soporta_datamatrix = models.BooleanField(default=False)
    
    # Estado
    activo = models.BooleanField(default=True)
    ubicacion = models.CharField(max_length=100)
    
    # Auditoría
    fecha_instalacion = models.DateTimeField(default=timezone.now)
    contador_lecturas = models.BigIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Escáner de Código de Barras'
        verbose_name_plural = 'Escáneres de Códigos de Barras'
        ordering = ['ubicacion', 'nombre']
        db_table = 'hw_escaner_codigo_barras'
    
    def __str__(self):
        return f"{self.nombre} - {self.ubicacion}"