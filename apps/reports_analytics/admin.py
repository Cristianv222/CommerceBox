# apps/reports_analytics/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import ReporteGuardado, ConfiguracionReporte, SnapshotDashboard


@admin.register(ReporteGuardado)
class ReporteGuardadoAdmin(admin.ModelAdmin):
    """
    Administración de reportes guardados
    """
    list_display = [
        'nombre',
        'tipo_reporte_display',
        'usuario',
        'periodo_display',
        'formato',
        'fecha_generacion',
        'acciones'
    ]
    list_filter = [
        'tipo_reporte',
        'formato',
        'fecha_generacion',
    ]
    search_fields = [
        'nombre',
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name'
    ]
    readonly_fields = [
        'fecha_generacion',
        'datos_json_display'
    ]
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo_reporte', 'formato')
        }),
        ('Período', {
            'fields': ('fecha_desde', 'fecha_hasta')
        }),
        ('Resultados', {
            'fields': ('resumen', 'datos_json_display', 'archivo')
        }),
        ('Auditoría', {
            'fields': ('usuario', 'fecha_generacion'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'fecha_generacion'
    
    def tipo_reporte_display(self, obj):
        return obj.get_tipo_reporte_display()
    tipo_reporte_display.short_description = 'Tipo de Reporte'
    
    def periodo_display(self, obj):
        return f"{obj.fecha_desde.strftime('%d/%m/%Y')} - {obj.fecha_hasta.strftime('%d/%m/%Y')}"
    periodo_display.short_description = 'Período'
    
    def datos_json_display(self, obj):
        """Muestra los datos JSON de forma legible"""
        import json
        try:
            formatted = json.dumps(obj.datos, indent=2, ensure_ascii=False)
            return format_html('<pre style="max-height: 400px; overflow: auto;">{}</pre>', formatted)
        except:
            return str(obj.datos)
    datos_json_display.short_description = 'Datos del Reporte'
    
    def acciones(self, obj):
        """Enlaces de acción"""
        if obj.archivo:
            download_url = reverse('reports_analytics:descargar_reporte', args=[obj.id])
            return format_html(
                '<a href="{}" class="button">Descargar</a>',
                download_url
            )
        return '-'
    acciones.short_description = 'Acciones'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusuarios ven todos, otros solo los suyos
        if not request.user.is_superuser:
            qs = qs.filter(usuario=request.user)
        return qs


@admin.register(ConfiguracionReporte)
class ConfiguracionReporteAdmin(admin.ModelAdmin):
    """
    Administración de configuraciones de reportes
    """
    list_display = [
        'nombre_configuracion',
        'usuario',
        'tipo_reporte_display',
        'es_predeterminada',
        'fecha_creacion'
    ]
    list_filter = [
        'tipo_reporte',
        'es_predeterminada',
        'fecha_creacion'
    ]
    search_fields = [
        'nombre_configuracion',
        'usuario__username'
    ]
    readonly_fields = [
        'fecha_creacion',
        'fecha_actualizacion',
        'configuracion_json_display'
    ]
    fieldsets = (
        ('Identificación', {
            'fields': ('nombre_configuracion', 'tipo_reporte', 'usuario')
        }),
        ('Configuración', {
            'fields': ('configuracion_json_display', 'es_predeterminada')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def tipo_reporte_display(self, obj):
        return obj.get_tipo_reporte_display()
    tipo_reporte_display.short_description = 'Tipo de Reporte'
    
    def configuracion_json_display(self, obj):
        """Muestra la configuración JSON de forma legible"""
        import json
        try:
            formatted = json.dumps(obj.configuracion, indent=2, ensure_ascii=False)
            return format_html('<pre style="max-height: 400px; overflow: auto;">{}</pre>', formatted)
        except:
            return str(obj.configuracion)
    configuracion_json_display.short_description = 'Configuración'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(usuario=request.user)
        return qs


@admin.register(SnapshotDashboard)
class SnapshotDashboardAdmin(admin.ModelAdmin):
    """
    Administración de snapshots del dashboard
    """
    list_display = [
        'fecha_snapshot',
        'tipo',
        'total_ventas_dia_display',
        'total_ventas_mes_display',
        'valor_inventario_display',
        'efectivo_caja_display'
    ]
    list_filter = [
        'tipo',
        'fecha_snapshot'
    ]
    readonly_fields = [
        'fecha_snapshot',
        'metricas_completas_display'
    ]
    fieldsets = (
        ('Información', {
            'fields': ('fecha_snapshot', 'tipo')
        }),
        ('Métricas Ventas', {
            'fields': (
                'total_ventas_dia',
                'total_ventas_mes',
                'numero_ventas_dia',
                'numero_ventas_mes'
            )
        }),
        ('Métricas Inventario', {
            'fields': (
                'valor_inventario_total',
                'productos_criticos',
                'productos_agotados'
            )
        }),
        ('Métricas Financieras', {
            'fields': ('efectivo_en_caja',)
        }),
        ('Datos Completos', {
            'fields': ('metricas_completas_display',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'fecha_snapshot'
    
    def total_ventas_dia_display(self, obj):
        return f"${obj.total_ventas_dia:,.2f}"
    total_ventas_dia_display.short_description = 'Ventas Día'
    
    def total_ventas_mes_display(self, obj):
        return f"${obj.total_ventas_mes:,.2f}"
    total_ventas_mes_display.short_description = 'Ventas Mes'
    
    def valor_inventario_display(self, obj):
        return f"${obj.valor_inventario_total:,.2f}"
    valor_inventario_display.short_description = 'Valor Inventario'
    
    def efectivo_caja_display(self, obj):
        return f"${obj.efectivo_en_caja:,.2f}"
    efectivo_caja_display.short_description = 'Efectivo en Caja'
    
    def metricas_completas_display(self, obj):
        """Muestra las métricas completas JSON"""
        import json
        try:
            formatted = json.dumps(obj.metricas_completas, indent=2, ensure_ascii=False)
            return format_html('<pre style="max-height: 400px; overflow: auto;">{}</pre>', formatted)
        except:
            return str(obj.metricas_completas)
    metricas_completas_display.short_description = 'Métricas Completas'
    
    def has_add_permission(self, request):
        # Solo permitir crear snapshots mediante código
        return False


# Configuración del sitio de administración
admin.site.site_header = "CommerceBox - Administración de Reportes"
admin.site.site_title = "Reportes y Análisis"
admin.site.index_title = "Panel de Administración de Reportes"