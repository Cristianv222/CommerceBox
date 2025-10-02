# apps/stock_alert_system/models.py

"""
Sistema de Alertas de Stock
Gestión automática de alertas de inventario
"""

import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.authentication.models import Usuario
from apps.inventory_management.models import Producto, Quintal, ProductoNormal


class AlertaStock(models.Model):
    """
    Modelo para gestionar alertas de stock del inventario
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
        """Días desde que se creó la alerta sin resolver"""
        if self.resuelta:
            return 0
        return (timezone.now() - self.fecha_creacion).days
    
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


class ConfiguracionAlerta(models.Model):
    """
    Configuración del sistema de alertas
    """
    
    # Umbrales
    umbral_stock_critico = models.IntegerField(
        default=5,
        help_text='Cantidad para considerar stock crítico'
    )
    umbral_stock_bajo = models.IntegerField(
        default=10,
        help_text='Cantidad para considerar stock bajo'
    )
    umbral_quintal_critico = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text='Porcentaje restante para considerar quintal crítico'
    )
    dias_vencimiento_proximo = models.IntegerField(
        default=7,
        help_text='Días para considerar vencimiento próximo'
    )
    
    # Notificaciones
    notificar_email = models.BooleanField(default=True)
    notificar_push = models.BooleanField(default=False)
    notificar_sms = models.BooleanField(default=False)
    
    # Emails de notificación
    emails_notificacion = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de emails para notificaciones'
    )
    
    # Control
    alertas_activas = models.BooleanField(
        default=True,
        help_text='Sistema de alertas activo'
    )
    auto_generar_alertas = models.BooleanField(
        default=True,
        help_text='Generar alertas automáticamente'
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de Alertas'
        verbose_name_plural = 'Configuraciones de Alertas'
    
    def __str__(self):
        return f"Configuración de Alertas (Actualizada: {self.fecha_actualizacion})"
    
    @classmethod
    def get_config(cls):
        """Obtiene o crea la configuración única"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class HistorialAlerta(models.Model):
    """
    Historial de cambios en las alertas
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
    
    def __str__(self):
        return f"{self.accion} - {self.alerta.titulo} ({self.fecha})"