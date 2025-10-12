# apps/stock_alert_system/models.py

"""
Sistema de Alertas de Stock - Versión Híbrida Mejorada
Combina sistema existente con nuevas funcionalidades de semáforos
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, Q

from apps.authentication.models import Usuario
from apps.inventory_management.models import Producto, Quintal, ProductoNormal


# ============================================================================
# CONFIGURACIÓN DE ALERTAS (MEJORADA - Fusión de ambas versiones)
# ============================================================================

class ConfiguracionAlerta(models.Model):
    """
    Configuración global del sistema de alertas
    Combina umbrales para productos normales y quintales
    """
    
    # ==========================================
    # UMBRALES PARA PRODUCTOS NORMALES
    # ==========================================
    umbral_stock_critico = models.IntegerField(
        default=5,
        help_text='Cantidad para considerar stock crítico en productos normales'
    )
    umbral_stock_bajo = models.IntegerField(
        default=10,
        help_text='Cantidad para considerar stock bajo en productos normales'
    )
    multiplicador_stock_bajo = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.00,
        help_text="Stock bajo = stock_minimo × este multiplicador (ej: 2.0 = el doble)"
    )
    
    # ==========================================
    # UMBRALES PARA QUINTALES (Por porcentaje)
    # ==========================================
    umbral_quintal_critico = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text='Porcentaje restante para considerar quintal crítico (ej: 10.00 = 10%)'
    )
    umbral_quintal_bajo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=25.00,
        help_text='Porcentaje restante para considerar quintal bajo (ej: 25.00 = 25%)'
    )
    
    # ==========================================
    # ALERTAS DE VENCIMIENTO
    # ==========================================
    dias_vencimiento_proximo = models.IntegerField(
        default=7,
        help_text='Días antes del vencimiento para generar alerta'
    )
    
    # ==========================================
    # NOTIFICACIONES
    # ==========================================
    notificar_email = models.BooleanField(
        default=True,
        help_text='Enviar notificaciones por email'
    )
    notificar_push = models.BooleanField(
        default=False,
        help_text='Enviar notificaciones push (futuro)'
    )
    notificar_sms = models.BooleanField(
        default=False,
        help_text='Enviar notificaciones SMS (futuro)'
    )
    emails_notificacion = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de emails para recibir notificaciones'
    )
    
    # ==========================================
    # CONTROL DEL SISTEMA
    # ==========================================
    alertas_activas = models.BooleanField(
        default=True,
        help_text='Sistema de alertas activo globalmente'
    )
    auto_generar_alertas = models.BooleanField(
        default=True,
        help_text='Generar alertas automáticamente al detectar cambios'
    )
    
    # ==========================================
    # AUDITORÍA
    # ==========================================
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configuraciones_alertas'
    )
    
    class Meta:
        verbose_name = 'Configuración de Alertas'
        verbose_name_plural = 'Configuraciones de Alertas'
        db_table = 'stock_alert_configuracion'
    
    def __str__(self):
        return f"Configuración de Alertas (Actualizada: {self.fecha_actualizacion.strftime('%d/%m/%Y')})"
    
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
                'umbral_stock_critico': 5,
                'umbral_stock_bajo': 10,
                'umbral_quintal_critico': Decimal('10.00'),
                'umbral_quintal_bajo': Decimal('25.00'),
                'multiplicador_stock_bajo': Decimal('2.00'),
                'dias_vencimiento_proximo': 7,
                'alertas_activas': True,
                'auto_generar_alertas': True,
                'notificar_email': True,
            }
        )
        return config
    
    @classmethod
    def get_configuracion(cls):
        """
        Alias de get_config() para compatibilidad con status_calculator.py
        """
        return cls.get_config()
    
    @property
    def dias_alerta_vencimiento(self):
        """
        Alias de dias_vencimiento_proximo para compatibilidad
        """
        return self.dias_vencimiento_proximo


# ============================================================================
# ESTADO DE STOCK (NUEVO - Corazón del sistema de semáforos) ⭐
# ============================================================================

class EstadoStock(models.Model):
    """
    Estado actual de stock para cada producto con semáforo
    Se actualiza automáticamente con signals
    
    ESTE ES EL MODELO CLAVE que permite:
    - Consultas rápidas del estado actual
    - Semáforos visuales 🟢🟡🔴⚫
    - Dashboard en tiempo real
    """
    
    TIPO_INVENTARIO_CHOICES = [
        ('QUINTAL', 'Quintal'),
        ('NORMAL', 'Producto Normal'),
    ]
    
    ESTADO_SEMAFORO_CHOICES = [
        ('NORMAL', '🟢 Normal - Stock saludable'),
        ('BAJO', '🟡 Bajo - Necesita atención'),
        ('CRITICO', '🔴 Crítico - Reorden urgente'),
        ('AGOTADO', '⚫ Agotado - Sin stock'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación al producto (OneToOne - un solo estado por producto)
    producto = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE,
        related_name='estado_stock',
        help_text="Producto al que pertenece este estado"
    )
    
    # Tipo y estado
    tipo_inventario = models.CharField(
        max_length=20,
        choices=TIPO_INVENTARIO_CHOICES,
        db_index=True
    )
    estado_semaforo = models.CharField(
        max_length=20,
        choices=ESTADO_SEMAFORO_CHOICES,
        default='NORMAL',
        db_index=True,
        help_text="Estado del semáforo actual"
    )
    
    # ==========================================
    # DATOS PARA QUINTALES
    # ==========================================
    total_quintales = models.IntegerField(
        default=0,
        help_text="Total de quintales disponibles"
    )
    peso_total_disponible = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Peso total disponible en todos los quintales"
    )
    peso_total_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Peso inicial total (para calcular porcentaje)"
    )
    porcentaje_disponible = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="% de peso disponible vs inicial"
    )
    
    # ==========================================
    # DATOS PARA PRODUCTOS NORMALES
    # ==========================================
    stock_actual = models.IntegerField(
        default=0,
        help_text="Stock actual en unidades"
    )
    stock_minimo = models.IntegerField(
        default=0,
        help_text="Stock mínimo configurado"
    )
    stock_maximo = models.IntegerField(
        null=True,
        blank=True,
        help_text="Stock máximo configurado"
    )
    
    # ==========================================
    # CAMPOS COMUNES
    # ==========================================
    requiere_atencion = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Marca si requiere atención inmediata (CRÍTICO o AGOTADO)"
    )
    valor_inventario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Valor monetario del inventario disponible"
    )
    
    # Auditoría
    fecha_ultimo_calculo = models.DateTimeField(
        default=timezone.now,
        help_text="Última vez que se calculó el estado"
    )
    fecha_cambio_estado = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última vez que cambió el estado del semáforo"
    )
    
    class Meta:
        verbose_name = 'Estado de Stock'
        verbose_name_plural = 'Estados de Stock'
        ordering = ['estado_semaforo', 'producto__nombre']
        db_table = 'stock_alert_estado_stock'
        indexes = [
            models.Index(fields=['estado_semaforo', 'requiere_atencion']),
            models.Index(fields=['tipo_inventario', 'estado_semaforo']),
            models.Index(fields=['producto', 'estado_semaforo']),
        ]
    
    def __str__(self):
        return f"{self.get_icono_semaforo()} {self.producto.nombre} - {self.get_estado_semaforo_display()}"
    
    def get_icono_semaforo(self):
        """Retorna el emoji del semáforo"""
        iconos = {
            'NORMAL': '🟢',
            'BAJO': '🟡',
            'CRITICO': '🔴',
            'AGOTADO': '⚫'
        }
        return iconos.get(self.estado_semaforo, '⚪')
    
    def get_color_css(self):
        """Retorna clase CSS para el color (Bootstrap)"""
        colores = {
            'NORMAL': 'success',
            'BAJO': 'warning',
            'CRITICO': 'danger',
            'AGOTADO': 'dark'
        }
        return colores.get(self.estado_semaforo, 'secondary')
    
    def necesita_reorden(self):
        """Verifica si necesita reorden urgente"""
        return self.estado_semaforo in ['CRITICO', 'AGOTADO']
    
    def actualizar_estado(self):
        """
        Recalcula el estado actual del stock
        Llama al servicio status_calculator
        """
        from .status_calculator import StatusCalculator
        StatusCalculator.calcular_estado(self.producto)


# ============================================================================
# ALERTAS DE STOCK (Tu modelo original - Mantenerlo)
# ============================================================================

class AlertaStock(models.Model):
    """
    Modelo para gestionar alertas de stock del inventario
    Sistema original mantenido para compatibilidad
    """
    
    TIPO_ALERTA_CHOICES = [
        ('STOCK_BAJO', 'Stock Bajo'),
        ('STOCK_CRITICO', 'Stock Crítico'),
        ('STOCK_AGOTADO', 'Stock Agotado'),
        ('QUINTAL_CRITICO', 'Quintal Crítico'),
        ('QUINTAL_AGOTADO', 'Quintal Agotado'),
        ('VENCIMIENTO_PROXIMO', 'Vencimiento Próximo'),
        ('PRODUCTO_VENCIDO', 'Producto Vencido'),
        ('REORDEN_NECESARIO', 'Reorden Necesario'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('VISTA', 'Vista'),
        ('EN_PROCESO', 'En Proceso'),
        ('RESUELTA', 'Resuelta'),
        ('IGNORADA', 'Ignorada'),
    ]
    
    # Identificación
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tipo y prioridad
    tipo_alerta = models.CharField(
        max_length=30,
        choices=TIPO_ALERTA_CHOICES,
        db_index=True
    )
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='MEDIA',
        db_index=True
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    
    # Referencias (solo una debe estar presente)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='alertas',
        null=True,
        blank=True
    )
    quintal = models.ForeignKey(
        Quintal,
        on_delete=models.CASCADE,
        related_name='alertas',
        null=True,
        blank=True
    )
    producto_normal = models.ForeignKey(
        ProductoNormal,
        on_delete=models.CASCADE,
        related_name='alertas',
        null=True,
        blank=True
    )
    
    # NUEVO: Relación al estado de stock
    estado_stock = models.ForeignKey(
        EstadoStock,
        on_delete=models.CASCADE,
        related_name='alertas',
        null=True,
        blank=True,
        help_text="Estado de stock asociado a esta alerta"
    )
    
    # Información de la alerta
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    datos_adicionales = models.JSONField(default=dict, blank=True)
    
    # Control
    resuelta = models.BooleanField(default=False, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_vista = models.DateTimeField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    
    # Usuarios
    usuario_asignado = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name='alertas_asignadas',
        null=True,
        blank=True
    )
    usuario_resolutor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name='alertas_resueltas',
        null=True,
        blank=True
    )
    
    # Notas
    notas = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Alerta de Stock'
        verbose_name_plural = 'Alertas de Stock'
        ordering = ['-prioridad', '-fecha_creacion']
        db_table = 'stock_alert_alerta'
        indexes = [
            models.Index(fields=['tipo_alerta', 'resuelta']),
            models.Index(fields=['prioridad', 'estado']),
            models.Index(fields=['fecha_creacion', 'resuelta']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_alerta_display()} - {self.titulo}"
    
    def clean(self):
        """Validar que solo una referencia esté presente"""
        referencias = sum([
            self.producto is not None,
            self.quintal is not None,
            self.producto_normal is not None
        ])
        
        if referencias == 0:
            raise ValidationError('Debe tener al menos una referencia (producto, quintal o producto_normal)')
        
        if referencias > 1:
            raise ValidationError('Solo puede tener una referencia (producto, quintal o producto_normal)')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def marcar_vista(self, usuario=None):
        """Marcar la alerta como vista"""
        if self.estado == 'PENDIENTE':
            self.estado = 'VISTA'
            self.fecha_vista = timezone.now()
            if usuario:
                self.usuario_asignado = usuario
            self.save()
    
    def marcar_en_proceso(self, usuario=None):
        """Marcar la alerta como en proceso"""
        self.estado = 'EN_PROCESO'
        if usuario and not self.usuario_asignado:
            self.usuario_asignado = usuario
        self.save()
    
    def resolver(self, usuario=None, notas=''):
        """Resolver la alerta"""
        self.estado = 'RESUELTA'
        self.resuelta = True
        self.fecha_resolucion = timezone.now()
        
        if usuario:
            self.usuario_resolutor = usuario
        
        if notas:
            if self.notas:
                self.notas += f"\n\n[{timezone.now()}] {notas}"
            else:
                self.notas = notas
        
        self.save()
    
    def ignorar(self, usuario=None, razon=''):
        """Ignorar la alerta"""
        self.estado = 'IGNORADA'
        self.resuelta = True
        self.fecha_resolucion = timezone.now()
        
        if usuario:
            self.usuario_resolutor = usuario
        
        if razon:
            self.notas = f"Ignorada: {razon}"
        
        self.save()
    
    def es_critica(self):
        """Verifica si la alerta es crítica"""
        return self.prioridad == 'CRITICA'
    
    def dias_sin_resolver(self):
        """
        Días desde que se creó la alerta sin resolver
        
        🔧 FIX APLICADO: Verifica que fecha_creacion exista antes de usarla
        Esto previene el TypeError cuando se crea una nueva alerta en el admin
        """
        if self.resuelta:
            return 0
        
        # FIX: Verificar si fecha_creacion existe (puede ser None en objetos nuevos)
        if not self.fecha_creacion:
            return 0
        
        return (timezone.now() - self.fecha_creacion).days
    
    def get_icono_prioridad(self):
        """Retorna icono según prioridad"""
        iconos = {
            'BAJA': 'ℹ️',
            'MEDIA': '⚠️',
            'ALTA': '🔥',
            'CRITICA': '🚨'
        }
        return iconos.get(self.prioridad, '⚠️')
    
    def get_referencia(self):
        """Obtiene la referencia principal de la alerta"""
        if self.quintal:
            return self.quintal
        elif self.producto_normal:
            return self.producto_normal
        elif self.producto:
            return self.producto
        return None
    
    def get_referencia_nombre(self):
        """Obtiene el nombre de la referencia"""
        if self.quintal:
            return f"Quintal: {self.quintal.codigo_unico}"
        elif self.producto_normal:
            return f"Producto: {self.producto_normal.producto.nombre}"
        elif self.producto:
            return f"Producto: {self.producto.nombre}"
        return "Sin referencia"
    
    @property
    def notas_resolucion(self):
        """
        Alias de notas para compatibilidad con status_calculator.py
        """
        return self.notas
    
    @notas_resolucion.setter
    def notas_resolucion(self, value):
        """
        Setter para notas_resolucion
        """
        self.notas = value
    
    @property
    def fecha_resuelta(self):
        """
        Alias de fecha_resolucion para compatibilidad
        """
        return self.fecha_resolucion
    
    @fecha_resuelta.setter
    def fecha_resuelta(self, value):
        """
        Setter para fecha_resuelta
        """
        self.fecha_resolucion = value
    
    def is_activa(self):
        """
        Verifica si la alerta está activa (no resuelta)
        Para compatibilidad con status_calculator.py que usa estado='ACTIVA'
        """
        return not self.resuelta and self.estado in ['PENDIENTE', 'VISTA', 'EN_PROCESO']
    
    @staticmethod
    def get_prioridad_por_tipo(tipo_alerta):
        """Determina la prioridad según el tipo de alerta"""
        prioridades_alta = ['STOCK_AGOTADO', 'QUINTAL_AGOTADO', 'PRODUCTO_VENCIDO']
        prioridades_critica = ['STOCK_CRITICO', 'QUINTAL_CRITICO']
        
        if tipo_alerta in prioridades_critica:
            return 'CRITICA'
        elif tipo_alerta in prioridades_alta:
            return 'ALTA'
        else:
            return 'MEDIA'


# ============================================================================
# HISTORIAL DE ALERTAS (Tu modelo original - Mantenerlo)
# ============================================================================

class HistorialAlerta(models.Model):
    """
    Historial de cambios en las alertas
    Sistema original mantenido para auditoría
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    alerta = models.ForeignKey(
        AlertaStock,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    
    accion = models.CharField(max_length=50)
    descripcion = models.TextField()
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    fecha = models.DateTimeField(auto_now_add=True)
    datos_adicionales = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Historial de Alerta'
        verbose_name_plural = 'Historiales de Alertas'
        ordering = ['-fecha']
        db_table = 'stock_alert_historial'
    
    def __str__(self):
        return f"{self.accion} - {self.alerta.titulo} ({self.fecha.strftime('%d/%m/%Y %H:%M')})"


# ============================================================================
# HISTORIAL DE ESTADOS (NUEVO - Para auditoría de cambios de semáforo)
# ============================================================================

class HistorialEstado(models.Model):
    """
    Registro histórico de cambios de estado de stock
    Para análisis y auditoría de cambios de semáforo
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relaciones
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='historial_estados'
    )
    estado_stock = models.ForeignKey(
        EstadoStock,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    
    # Estados
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    
    # Datos del cambio
    tipo_inventario = models.CharField(max_length=20)
    stock_anterior = models.DecimalField(max_digits=12, decimal_places=3)
    stock_nuevo = models.DecimalField(max_digits=12, decimal_places=3)
    
    # Causa del cambio
    motivo_cambio = models.CharField(
        max_length=50,
        blank=True,
        help_text="Venta, Ajuste, Compra, etc"
    )
    
    # Auditoría
    fecha_cambio = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Historial de Estado'
        verbose_name_plural = 'Historial de Estados'
        ordering = ['-fecha_cambio']
        db_table = 'stock_alert_historial_estado'
        indexes = [
            models.Index(fields=['producto', '-fecha_cambio']),
            models.Index(fields=['estado_nuevo', '-fecha_cambio']),
        ]
    
    def __str__(self):
        return f"{self.producto.nombre}: {self.estado_anterior} → {self.estado_nuevo}"


# ============================================================================
# FUNCIONES HELPER GLOBALES
# ============================================================================

def get_estadisticas_globales():
    """
    Retorna estadísticas globales del sistema de alertas
    """
    total_productos = EstadoStock.objects.count()
    
    stats = {
        'total_productos': total_productos,
        'productos_criticos': EstadoStock.objects.filter(estado_semaforo='CRITICO').count(),
        'productos_bajos': EstadoStock.objects.filter(estado_semaforo='BAJO').count(),
        'productos_agotados': EstadoStock.objects.filter(estado_semaforo='AGOTADO').count(),
        'productos_normales': EstadoStock.objects.filter(estado_semaforo='NORMAL').count(),
        'alertas_activas': AlertaStock.objects.filter(resuelta=False).count(),
        'alertas_criticas': AlertaStock.objects.filter(resuelta=False, prioridad='CRITICA').count(),
    }
    
    # Porcentajes
    if total_productos > 0:
        stats['porcentaje_criticos'] = (stats['productos_criticos'] / total_productos) * 100
        stats['porcentaje_bajos'] = (stats['productos_bajos'] / total_productos) * 100
        stats['porcentaje_agotados'] = (stats['productos_agotados'] / total_productos) * 100
        stats['porcentaje_normales'] = (stats['productos_normales'] / total_productos) * 100
    else:
        stats['porcentaje_criticos'] = 0
        stats['porcentaje_bajos'] = 0
        stats['porcentaje_agotados'] = 0
        stats['porcentaje_normales'] = 0
    
    return stats


# ============================================================================
# ALIAS DE COMPATIBILIDAD
# ============================================================================
# Tu status_calculator.py usa "Alerta", pero el modelo se llama "AlertaStock"
# Este alias permite que ambos nombres funcionen
Alerta = AlertaStock