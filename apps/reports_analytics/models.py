# apps/reports_analytics/models.py

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


# ============================================================================
# REPORTE GUARDADO
# ============================================================================

class ReporteGuardado(models.Model):
    """
    Reportes generados que se guardan para consulta posterior
    """
    TIPO_REPORTE_CHOICES = [
        ('VENTAS_DIARIAS', 'Ventas Diarias'),
        ('VENTAS_MENSUALES', 'Ventas Mensuales'),
        ('INVENTARIO_VALORIZADO', 'Inventario Valorizado'),
        ('RENTABILIDAD_PRODUCTOS', 'Rentabilidad por Producto'),
        ('MOVIMIENTOS_CAJA', 'Movimientos de Caja'),
        ('TRAZABILIDAD_QUINTALES', 'Trazabilidad de Quintales'),
        ('PRODUCTOS_CRITICOS', 'Productos Críticos'),
        ('COMPARATIVO_PERIODOS', 'Comparativo entre Períodos'),
        ('ARQUEOS_CAJA', 'Arqueos de Caja'),
        ('ANALISIS_CLIENTES', 'Análisis de Clientes'),
        ('VENTAS_POR_VENDEDOR', 'Ventas por Vendedor'),
        ('DASHBOARD_EJECUTIVO', 'Dashboard Ejecutivo'),
    ]
    
    FORMATO_CHOICES = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
        ('JSON', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    nombre = models.CharField(
        max_length=200,
        help_text="Nombre descriptivo del reporte"
    )
    tipo_reporte = models.CharField(
        max_length=50,
        choices=TIPO_REPORTE_CHOICES,
        db_index=True
    )
    
    # Período del reporte
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    
    # Filtros aplicados (JSON)
    filtros = models.JSONField(
        default=dict,
        blank=True,
        help_text="Filtros aplicados en formato JSON"
    )
    
    # Datos del reporte (JSON)
    datos = models.JSONField(
        default=dict,
        help_text="Datos calculados del reporte"
    )
    
    # Resumen ejecutivo
    resumen = models.TextField(
        blank=True,
        help_text="Resumen ejecutivo del reporte"
    )
    
    # Archivo generado
    formato = models.CharField(
        max_length=10,
        choices=FORMATO_CHOICES,
        default='PDF'
    )
    archivo = models.FileField(
        upload_to='reportes/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Auditoría
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='reportes_generados'
    )
    fecha_generacion = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Reporte Guardado'
        verbose_name_plural = 'Reportes Guardados'
        ordering = ['-fecha_generacion']
        db_table = 'rpt_reporte_guardado'
        indexes = [
            models.Index(fields=['tipo_reporte', '-fecha_generacion']),
            models.Index(fields=['usuario', '-fecha_generacion']),
            models.Index(fields=['fecha_desde', 'fecha_hasta']),
        ]
    
    def __str__(self):
        return f"{self.nombre} - {self.fecha_generacion.strftime('%d/%m/%Y')}"


# ============================================================================
# CONFIGURACIÓN DE REPORTES
# ============================================================================

class ConfiguracionReporte(models.Model):
    """
    Configuraciones personalizadas para reportes
    Permite a usuarios guardar sus configuraciones favoritas
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Usuario y tipo
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.CASCADE,
        related_name='configuraciones_reportes'
    )
    tipo_reporte = models.CharField(
        max_length=50,
        choices=ReporteGuardado.TIPO_REPORTE_CHOICES
    )
    
    # Nombre de la configuración
    nombre_configuracion = models.CharField(
        max_length=100,
        help_text="Nombre para identificar esta configuración"
    )
    
    # Configuración (JSON)
    configuracion = models.JSONField(
        default=dict,
        help_text="Filtros, columnas, formatos preferidos"
    )
    
    # Es configuración por defecto para este tipo de reporte
    es_predeterminada = models.BooleanField(default=False)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de Reporte'
        verbose_name_plural = 'Configuraciones de Reportes'
        unique_together = ['usuario', 'tipo_reporte', 'nombre_configuracion']
        db_table = 'rpt_configuracion_reporte'
    
    def __str__(self):
        return f"{self.nombre_configuracion} - {self.get_tipo_reporte_display()}"


# ============================================================================
# SNAPSHOT DE DASHBOARD (Para histórico)
# ============================================================================

class SnapshotDashboard(models.Model):
    """
    Guarda snapshots del dashboard en momentos específicos
    Útil para comparar rendimiento a lo largo del tiempo
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Fecha del snapshot
    fecha_snapshot = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # Métricas principales
    total_ventas_dia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_ventas_mes = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    numero_ventas_dia = models.IntegerField(default=0)
    numero_ventas_mes = models.IntegerField(default=0)
    
    # Inventario
    valor_inventario_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    productos_criticos = models.IntegerField(default=0)
    productos_agotados = models.IntegerField(default=0)
    
    # Caja
    efectivo_en_caja = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Datos completos (JSON)
    metricas_completas = models.JSONField(
        default=dict,
        help_text="Todas las métricas del dashboard"
    )
    
    # Tipo de snapshot
    TIPO_CHOICES = [
        ('AUTOMATICO', 'Automático (cada hora)'),
        ('CIERRE_DIA', 'Cierre de día'),
        ('MANUAL', 'Manual'),
    ]
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='AUTOMATICO'
    )
    
    class Meta:
        verbose_name = 'Snapshot de Dashboard'
        verbose_name_plural = 'Snapshots de Dashboard'
        ordering = ['-fecha_snapshot']
        db_table = 'rpt_snapshot_dashboard'
        indexes = [
            models.Index(fields=['-fecha_snapshot']),
            models.Index(fields=['tipo', '-fecha_snapshot']),
        ]
    
    def __str__(self):
        return f"Snapshot - {self.fecha_snapshot.strftime('%d/%m/%Y %H:%M')}"


# ============================================================================
# SIGNALS
# ============================================================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=ConfiguracionReporte)
def configuracion_predeterminada(sender, instance, created, **kwargs):
    """
    Si se marca como predeterminada, desmarcar otras del mismo tipo
    """
    if instance.es_predeterminada:
        ConfiguracionReporte.objects.filter(
            usuario=instance.usuario,
            tipo_reporte=instance.tipo_reporte
        ).exclude(id=instance.id).update(es_predeterminada=False)