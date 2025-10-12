# apps/stock_alert_system/admin.py

"""
Panel de Administración - Sistema de Alertas de Stock
Incluye interfaces completas para gestionar alertas, estados y configuración
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
from django.shortcuts import redirect

from .models import (
    ConfiguracionAlerta,
    EstadoStock,
    AlertaStock,
    HistorialAlerta,
    HistorialEstado
)


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    """
    Admin para la configuración global del sistema de alertas
    Solo permite un registro (Singleton)
    """
    
    fieldsets = (
        ('📦 Umbrales para Productos Normales', {
            'fields': (
                'umbral_stock_critico',
                'umbral_stock_bajo',
                'multiplicador_stock_bajo',
            ),
            'description': 'Configuración de umbrales para productos con unidades'
        }),
        ('⚖️ Umbrales para Quintales (Porcentaje)', {
            'fields': (
                'umbral_quintal_critico',
                'umbral_quintal_bajo',
            ),
            'description': 'Configuración de umbrales basados en porcentaje restante'
        }),
        ('📅 Alertas de Vencimiento', {
            'fields': (
                'dias_vencimiento_proximo',
            ),
        }),
        ('🔔 Configuración de Notificaciones', {
            'fields': (
                'notificar_email',
                'notificar_push',
                'notificar_sms',
                'emails_notificacion',
            ),
            'classes': ('collapse',),
        }),
        ('⚙️ Control del Sistema', {
            'fields': (
                'alertas_activas',
                'auto_generar_alertas',
            ),
        }),
        ('📋 Auditoría', {
            'fields': (
                'actualizado_por',
                'fecha_creacion',
                'fecha_actualizacion',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    def has_add_permission(self, request):
        """Solo permite un registro (Singleton)"""
        return not ConfiguracionAlerta.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """No permite eliminar la configuración"""
        return False
    
    def save_model(self, request, obj, form, change):
        """Guarda quién modificó la configuración"""
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# ESTADO DE STOCK (CORE DEL SISTEMA) ⭐
# ============================================================================

@admin.register(EstadoStock)
class EstadoStockAdmin(admin.ModelAdmin):
    """
    Admin principal para ver el estado de stock con semáforos
    Dashboard central del sistema de alertas
    """
    
    list_display = (
        'semaforo_visual',
        'producto_link',
        'tipo_inventario',
        'info_stock',
        'porcentaje_barra',
        'requiere_atencion_badge',
        'valor_total',
        'ultima_actualizacion',
        'acciones_rapidas',
    )
    
    list_filter = (
        'estado_semaforo',
        'tipo_inventario',
        'requiere_atencion',
        ('fecha_ultimo_calculo', admin.DateFieldListFilter),
    )
    
    search_fields = (
        'producto__nombre',
        'producto__codigo',
        'producto__codigo_barras',
    )
    
    readonly_fields = (
        'id',
        'producto',
        'tipo_inventario',
        'semaforo_grande',
        'grafico_estado',
        'fecha_ultimo_calculo',
        'fecha_cambio_estado',
        'detalles_completos',
    )
    
    fieldsets = (
        ('🚦 Estado Actual', {
            'fields': (
                'semaforo_grande',
                'producto',
                'tipo_inventario',
                'estado_semaforo',
                'requiere_atencion',
            ),
        }),
        ('📊 Datos de Quintales', {
            'fields': (
                'total_quintales',
                'peso_total_disponible',
                'peso_total_inicial',
                'porcentaje_disponible',
                'grafico_estado',
            ),
            'classes': ('collapse',),
        }),
        ('📦 Datos de Productos Normales', {
            'fields': (
                'stock_actual',
                'stock_minimo',
                'stock_maximo',
            ),
            'classes': ('collapse',),
        }),
        ('💰 Valor', {
            'fields': (
                'valor_inventario',
            ),
        }),
        ('🕐 Auditoría', {
            'fields': (
                'fecha_ultimo_calculo',
                'fecha_cambio_estado',
            ),
            'classes': ('collapse',),
        }),
        ('📋 Detalles Completos', {
            'fields': (
                'detalles_completos',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = [
        'recalcular_estados',
        'marcar_requiere_atencion',
        'desmarcar_requiere_atencion',
    ]
    
    # ==========================================
    # MÉTODOS DE VISUALIZACIÓN
    # ==========================================
    
    @admin.display(description='🚦 Estado', ordering='estado_semaforo')
    def semaforo_visual(self, obj):
        """Muestra el semáforo con emoji grande"""
        colores_bg = {
            'NORMAL': '#28a745',
            'BAJO': '#ffc107',
            'CRITICO': '#dc3545',
            'AGOTADO': '#343a40',
        }
        color = colores_bg.get(obj.estado_semaforo, '#6c757d')
        
        return format_html(
            '<div style="text-align: center;">'
            '<span style="font-size: 24px;">{}</span><br>'
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>'
            '</div>',
            obj.get_icono_semaforo(),
            color,
            obj.get_estado_semaforo_display().split('-')[0].strip()
        )
    
    @admin.display(description='Producto', ordering='producto__nombre')
    def producto_link(self, obj):
        """Link al producto"""
        url = reverse('admin:inventory_management_producto_change', args=[obj.producto.id])
        return format_html(
            '<a href="{}" style="font-weight: bold;">{}</a><br>'
            '<small style="color: #666;">{}</small>',
            url,
            obj.producto.nombre,
            obj.producto.codigo
        )
    
    @admin.display(description='Stock/Peso')
    def info_stock(self, obj):
        """Muestra información de stock según el tipo"""
        if obj.tipo_inventario == 'QUINTAL':
            return format_html(
                '<strong>{}</strong> quintales<br>'
                '<small>{:.2f} kg disponibles</small>',
                obj.total_quintales,
                obj.peso_total_disponible
            )
        else:
            min_display = f' / Min: {obj.stock_minimo}' if obj.stock_minimo else ''
            return format_html(
                '<strong>{}</strong> unidades{}<br>'
                '<small>Mín: {} | Máx: {}</small>',
                obj.stock_actual,
                min_display,
                obj.stock_minimo or '-',
                obj.stock_maximo or '-'
            )
    
    @admin.display(description='Nivel')
    def porcentaje_barra(self, obj):
        """Barra de progreso visual"""
        if obj.tipo_inventario == 'QUINTAL':
            porcentaje = float(obj.porcentaje_disponible)
        else:
            if obj.stock_maximo and obj.stock_maximo > 0:
                porcentaje = (obj.stock_actual / obj.stock_maximo) * 100
            else:
                porcentaje = 50  # Default si no hay máximo
        
        # Color según el porcentaje
        if porcentaje <= 10:
            color = '#dc3545'  # Rojo
        elif porcentaje <= 25:
            color = '#ffc107'  # Amarillo
        else:
            color = '#28a745'  # Verde
        
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; height: 20px; position: relative;">'
            '<div style="width: {}%; background-color: {}; height: 100%; border-radius: 3px;"></div>'
            '<span style="position: absolute; top: 0; left: 0; right: 0; text-align: center; '
            'line-height: 20px; font-size: 11px; font-weight: bold; color: #000;">{:.1f}%</span>'
            '</div>',
            min(porcentaje, 100),
            color,
            porcentaje
        )
    
    @admin.display(description='⚠️', boolean=True)
    def requiere_atencion_badge(self, obj):
        """Badge de atención requerida"""
        return obj.requiere_atencion
    
    @admin.display(description='Valor', ordering='valor_inventario')
    def valor_total(self, obj):
        """Valor del inventario"""
        return format_html(
            '<span style="font-weight: bold; color: #28a745;">'
            'L. {:.2f}'
            '</span>',
            obj.valor_inventario
        )
    
    @admin.display(description='Última Act.', ordering='fecha_ultimo_calculo')
    def ultima_actualizacion(self, obj):
        """Muestra cuándo se actualizó"""
        diff = timezone.now() - obj.fecha_ultimo_calculo
        
        if diff.seconds < 60:
            tiempo = 'Hace menos de 1 min'
            color = '#28a745'
        elif diff.seconds < 3600:
            tiempo = f'Hace {diff.seconds // 60} min'
            color = '#28a745'
        elif diff.days == 0:
            tiempo = f'Hace {diff.seconds // 3600} hrs'
            color = '#ffc107'
        else:
            tiempo = f'Hace {diff.days} días'
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-size: 11px;">{}</span>',
            color,
            tiempo
        )
    
    @admin.display(description='Acciones')
    def acciones_rapidas(self, obj):
        """Botones de acción rápida"""
        return format_html(
            '<a class="button" href="#" onclick="return confirm(\'¿Recalcular estado?\');" '
            'style="padding: 3px 8px; font-size: 11px;">🔄 Recalcular</a>'
        )
    
    # ==========================================
    # CAMPOS READONLY DETALLADOS
    # ==========================================
    
    @admin.display(description='Semáforo Actual')
    def semaforo_grande(self, obj):
        """Semáforo visual grande para el detalle"""
        if not obj:
            return '-'
        
        colores_bg = {
            'NORMAL': '#28a745',
            'BAJO': '#ffc107',
            'CRITICO': '#dc3545',
            'AGOTADO': '#343a40',
        }
        
        color = colores_bg.get(obj.estado_semaforo, '#6c757d')
        
        return format_html(
            '<div style="text-align: center; padding: 20px; background-color: {}; '
            'color: white; border-radius: 8px; margin: 10px 0;">'
            '<div style="font-size: 48px; margin-bottom: 10px;">{}</div>'
            '<div style="font-size: 24px; font-weight: bold;">{}</div>'
            '<div style="font-size: 14px; margin-top: 5px; opacity: 0.9;">{}</div>'
            '</div>',
            color,
            obj.get_icono_semaforo(),
            obj.get_estado_semaforo_display().split('-')[1].strip(),
            'REQUIERE ATENCIÓN INMEDIATA' if obj.requiere_atencion else 'Sistema funcionando normalmente'
        )
    
    @admin.display(description='Gráfico de Estado')
    def grafico_estado(self, obj):
        """Gráfico visual del estado actual"""
        if not obj or obj.tipo_inventario != 'QUINTAL':
            return '-'
        
        porcentaje = float(obj.porcentaje_disponible)
        
        # Barras de diferentes colores
        return format_html(
            '<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">'
            '<div style="margin-bottom: 5px;"><strong>Peso Disponible:</strong> {:.2f} kg</div>'
            '<div style="margin-bottom: 5px;"><strong>Peso Inicial:</strong> {:.2f} kg</div>'
            '<div style="margin-bottom: 10px;"><strong>Porcentaje:</strong> {:.2f}%</div>'
            '<div style="background-color: #e9ecef; height: 30px; border-radius: 5px; position: relative; overflow: hidden;">'
            '<div style="background: linear-gradient(90deg, #28a745, #ffc107, #dc3545); '
            'width: {}%; height: 100%;"></div>'
            '<span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); '
            'font-weight: bold; color: #000;">{:.1f}%</span>'
            '</div>'
            '</div>',
            obj.peso_total_disponible,
            obj.peso_total_inicial,
            porcentaje,
            min(porcentaje, 100),
            porcentaje
        )
    
    @admin.display(description='Información Completa')
    def detalles_completos(self, obj):
        """Detalles completos del estado"""
        if not obj:
            return '-'
        
        html = '<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">'
        html += '<h3 style="margin-top: 0;">📊 Resumen Completo</h3>'
        
        html += f'<p><strong>Producto:</strong> {obj.producto.nombre}</p>'
        html += f'<p><strong>Tipo:</strong> {obj.get_tipo_inventario_display()}</p>'
        html += f'<p><strong>Estado:</strong> {obj.get_estado_semaforo_display()}</p>'
        
        if obj.tipo_inventario == 'QUINTAL':
            html += f'<p><strong>Quintales totales:</strong> {obj.total_quintales}</p>'
            html += f'<p><strong>Peso disponible:</strong> {obj.peso_total_disponible:.2f} kg</p>'
            html += f'<p><strong>Peso inicial:</strong> {obj.peso_total_inicial:.2f} kg</p>'
            html += f'<p><strong>Porcentaje disponible:</strong> {obj.porcentaje_disponible:.2f}%</p>'
        else:
            html += f'<p><strong>Stock actual:</strong> {obj.stock_actual} unidades</p>'
            html += f'<p><strong>Stock mínimo:</strong> {obj.stock_minimo} unidades</p>'
            if obj.stock_maximo:
                html += f'<p><strong>Stock máximo:</strong> {obj.stock_maximo} unidades</p>'
        
        html += f'<p><strong>Valor inventario:</strong> L. {obj.valor_inventario:.2f}</p>'
        html += f'<p><strong>Requiere atención:</strong> {"✅ SÍ" if obj.requiere_atencion else "❌ No"}</p>'
        html += f'<p><strong>Última actualización:</strong> {obj.fecha_ultimo_calculo.strftime("%d/%m/%Y %H:%M:%S")}</p>'
        
        if obj.fecha_cambio_estado:
            html += f'<p><strong>Último cambio de estado:</strong> {obj.fecha_cambio_estado.strftime("%d/%m/%Y %H:%M:%S")}</p>'
        
        html += '</div>'
        
        return format_html(html)
    
    # ==========================================
    # ACCIONES
    # ==========================================
    
    @admin.action(description='🔄 Recalcular estados seleccionados')
    def recalcular_estados(self, request, queryset):
        """Recalcula el estado de los productos seleccionados"""
        count = 0
        for estado in queryset:
            try:
                estado.actualizar_estado()
                count += 1
            except Exception as e:
                messages.error(request, f'Error al recalcular {estado.producto.nombre}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'✅ Se recalcularon {count} estados correctamente')
    
    @admin.action(description='⚠️ Marcar como requiere atención')
    def marcar_requiere_atencion(self, request, queryset):
        """Marca productos como que requieren atención"""
        count = queryset.update(requiere_atencion=True)
        messages.success(request, f'✅ {count} productos marcados como requieren atención')
    
    @admin.action(description='✅ Desmarcar requiere atención')
    def desmarcar_requiere_atencion(self, request, queryset):
        """Desmarca productos que requieren atención"""
        count = queryset.update(requiere_atencion=False)
        messages.success(request, f'✅ {count} productos desmarcados')
    
    # ==========================================
    # CONFIGURACIÓN ADICIONAL
    # ==========================================
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('producto')
    
    class Media:
        css = {
            'all': ('admin/css/custom_stock_alerts.css',)
        }


# ============================================================================
# INLINE: HISTORIAL DE ESTADOS
# ============================================================================

class HistorialEstadoInline(admin.TabularInline):
    """Inline para mostrar historial de estados en EstadoStock"""
    model = HistorialEstado
    extra = 0
    can_delete = False
    
    fields = (
        'fecha_cambio',
        'estado_anterior_visual',
        'estado_nuevo_visual',
        'stock_cambio',
        'motivo_cambio',
    )
    
    readonly_fields = (
        'fecha_cambio',
        'estado_anterior_visual',
        'estado_nuevo_visual',
        'stock_cambio',
        'motivo_cambio',
    )
    
    @admin.display(description='Estado Anterior')
    def estado_anterior_visual(self, obj):
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            obj.estado_anterior
        )
    
    @admin.display(description='Estado Nuevo')
    def estado_nuevo_visual(self, obj):
        colores = {
            'NORMAL': '#28a745',
            'BAJO': '#ffc107',
            'CRITICO': '#dc3545',
            'AGOTADO': '#343a40',
        }
        color = colores.get(obj.estado_nuevo, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.estado_nuevo
        )
    
    @admin.display(description='Cambio de Stock')
    def stock_cambio(self, obj):
        diff = obj.stock_nuevo - obj.stock_anterior
        color = '#28a745' if diff > 0 else '#dc3545'
        simbolo = '+' if diff > 0 else ''
        
        return format_html(
            '{:.2f} → {:.2f} <span style="color: {};">({}{:.2f})</span>',
            obj.stock_anterior,
            obj.stock_nuevo,
            color,
            simbolo,
            diff
        )


# ============================================================================
# ALERTAS DE STOCK
# ============================================================================

class HistorialAlertaInline(admin.TabularInline):
    """Inline para historial de alertas"""
    model = HistorialAlerta
    extra = 0
    can_delete = False
    
    fields = ('fecha', 'accion', 'descripcion', 'usuario')
    readonly_fields = ('fecha', 'accion', 'descripcion', 'usuario')
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AlertaStock)
class AlertaStockAdmin(admin.ModelAdmin):
    """
    Admin para gestionar alertas de stock
    """
    
    list_display = (
        'prioridad_badge',
        'tipo_badge',
        'titulo_corto',
        'producto_referencia',
        'estado_badge',
        'dias_pendiente',
        'usuario_asignado',
        'fecha_creacion',
        'acciones_alerta',
    )
    
    list_filter = (
        'tipo_alerta',
        'prioridad',
        'estado',
        'resuelta',
        ('fecha_creacion', admin.DateFieldListFilter),
        'usuario_asignado',
    )
    
    search_fields = (
        'titulo',
        'mensaje',
        'producto__nombre',
        'quintal__codigo_unico',
    )
    
    readonly_fields = (
        'id',
        'fecha_creacion',
        'fecha_vista',
        'fecha_resolucion',
        'info_completa',
    )
    
    fieldsets = (
        ('🚨 Información de la Alerta', {
            'fields': (
                'tipo_alerta',
                'prioridad',
                'estado',
                'titulo',
                'mensaje',
            ),
        }),
        ('📦 Referencias', {
            'fields': (
                'producto',
                'quintal',
                'producto_normal',
                'estado_stock',
            ),
        }),
        ('👥 Gestión', {
            'fields': (
                'usuario_asignado',
                'usuario_resolutor',
                'notas',
            ),
        }),
        ('📊 Datos Adicionales', {
            'fields': (
                'datos_adicionales',
            ),
            'classes': ('collapse',),
        }),
        ('🕐 Fechas', {
            'fields': (
                'fecha_creacion',
                'fecha_vista',
                'fecha_resolucion',
            ),
            'classes': ('collapse',),
        }),
        ('📋 Información Completa', {
            'fields': (
                'info_completa',
            ),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [HistorialAlertaInline]
    
    actions = [
        'marcar_vistas',
        'marcar_en_proceso',
        'resolver_alertas',
        'ignorar_alertas',
    ]
    
    # ==========================================
    # MÉTODOS DE VISUALIZACIÓN
    # ==========================================
    
    @admin.display(description='⚠️', ordering='prioridad')
    def prioridad_badge(self, obj):
        """Badge de prioridad con colores"""
        colores = {
            'BAJA': '#17a2b8',
            'MEDIA': '#ffc107',
            'ALTA': '#fd7e14',
            'CRITICA': '#dc3545',
        }
        
        return format_html(
            '<div style="text-align: center;">'
            '<span style="font-size: 20px;">{}</span><br>'
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>'
            '</div>',
            obj.get_icono_prioridad(),
            colores.get(obj.prioridad, '#6c757d'),
            obj.get_prioridad_display()
        )
    
    @admin.display(description='Tipo', ordering='tipo_alerta')
    def tipo_badge(self, obj):
        """Badge del tipo de alerta"""
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; display: inline-block; white-space: nowrap;">'
            '{}'
            '</span>',
            obj.get_tipo_alerta_display()
        )
    
    @admin.display(description='Título')
    def titulo_corto(self, obj):
        """Título con máximo de caracteres"""
        max_len = 50
        titulo = obj.titulo[:max_len] + '...' if len(obj.titulo) > max_len else obj.titulo
        return format_html('<strong>{}</strong>', titulo)
    
    @admin.display(description='Producto/Referencia')
    def producto_referencia(self, obj):
        """Muestra la referencia principal"""
        return format_html(
            '<span style="color: #495057;">{}</span>',
            obj.get_referencia_nombre()
        )
    
    @admin.display(description='Estado', ordering='estado')
    def estado_badge(self, obj):
        """Badge del estado con colores"""
        colores = {
            'PENDIENTE': '#6c757d',
            'VISTA': '#17a2b8',
            'EN_PROCESO': '#ffc107',
            'RESUELTA': '#28a745',
            'IGNORADA': '#dc3545',
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colores.get(obj.estado, '#6c757d'),
            obj.get_estado_display()
        )
    
    @admin.display(description='Días', ordering='fecha_creacion')
    def dias_pendiente(self, obj):
        """Días sin resolver con color según urgencia"""
        dias = obj.dias_sin_resolver()
        
        if dias == 0:
            return format_html('<span style="color: #28a745;">Resuelta</span>')
        
        if dias >= 7:
            color = '#dc3545'
        elif dias >= 3:
            color = '#fd7e14'
        else:
            color = '#ffc107'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} días</span>',
            color,
            dias
        )
    
    @admin.display(description='Acciones')
    def acciones_alerta(self, obj):
        """Botones de acción rápida"""
        if obj.resuelta:
            return format_html('<span style="color: #28a745;">✅ Resuelta</span>')
        
        return format_html(
            '<a class="button" href="#" style="padding: 3px 8px; font-size: 11px;">👁️ Ver</a> '
            '<a class="button" href="#" style="padding: 3px 8px; font-size: 11px;">✅ Resolver</a>'
        )
    
    @admin.display(description='Información Completa')
    def info_completa(self, obj):
        """Información completa de la alerta"""
        if not obj:
            return '-'
        
        html = '<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">'
        html += '<h3 style="margin-top: 0;">📋 Detalles de la Alerta</h3>'
        
        html += f'<p><strong>ID:</strong> {obj.id}</p>'
        html += f'<p><strong>Tipo:</strong> {obj.get_tipo_alerta_display()}</p>'
        html += f'<p><strong>Prioridad:</strong> {obj.get_prioridad_display()}</p>'
        html += f'<p><strong>Estado:</strong> {obj.get_estado_display()}</p>'
        html += f'<p><strong>Título:</strong> {obj.titulo}</p>'
        html += f'<p><strong>Mensaje:</strong> {obj.mensaje}</p>'
        html += f'<p><strong>Referencia:</strong> {obj.get_referencia_nombre()}</p>'
        
        if obj.usuario_asignado:
            html += f'<p><strong>Asignado a:</strong> {obj.usuario_asignado.username}</p>'
        
        if obj.usuario_resolutor:
            html += f'<p><strong>Resuelto por:</strong> {obj.usuario_resolutor.username}</p>'
        
        html += f'<p><strong>Creada:</strong> {obj.fecha_creacion.strftime("%d/%m/%Y %H:%M:%S")}</p>'
        
        if obj.fecha_vista:
            html += f'<p><strong>Vista:</strong> {obj.fecha_vista.strftime("%d/%m/%Y %H:%M:%S")}</p>'
        
        if obj.fecha_resolucion:
            html += f'<p><strong>Resuelta:</strong> {obj.fecha_resolucion.strftime("%d/%m/%Y %H:%M:%S")}</p>'
        
        if obj.notas:
            html += f'<p><strong>Notas:</strong><br>{obj.notas}</p>'
        
        html += '</div>'
        
        return format_html(html)
    
    # ==========================================
    # ACCIONES
    # ==========================================
    
    @admin.action(description='👁️ Marcar como vistas')
    def marcar_vistas(self, request, queryset):
        """Marca las alertas seleccionadas como vistas"""
        count = 0
        for alerta in queryset.filter(estado='PENDIENTE'):
            alerta.marcar_vista(request.user)
            count += 1
        
        messages.success(request, f'✅ {count} alertas marcadas como vistas')
    
    @admin.action(description='🔧 Marcar como en proceso')
    def marcar_en_proceso(self, request, queryset):
        """Marca las alertas como en proceso"""
        count = 0
        for alerta in queryset.filter(resuelta=False):
            alerta.marcar_en_proceso(request.user)
            count += 1
        
        messages.success(request, f'✅ {count} alertas marcadas como en proceso')
    
    @admin.action(description='✅ Resolver alertas')
    def resolver_alertas(self, request, queryset):
        """Resuelve las alertas seleccionadas"""
        count = 0
        for alerta in queryset.filter(resuelta=False):
            alerta.resolver(request.user, 'Resuelta desde admin')
            count += 1
        
        messages.success(request, f'✅ {count} alertas resueltas correctamente')
    
    @admin.action(description='❌ Ignorar alertas')
    def ignorar_alertas(self, request, queryset):
        """Ignora las alertas seleccionadas"""
        count = 0
        for alerta in queryset.filter(resuelta=False):
            alerta.ignorar(request.user, 'Ignorada desde admin')
            count += 1
        
        messages.warning(request, f'⚠️ {count} alertas ignoradas')
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'producto',
            'quintal',
            'producto_normal',
            'usuario_asignado',
            'usuario_resolutor'
        )


# ============================================================================
# HISTORIAL DE ALERTAS
# ============================================================================

@admin.register(HistorialAlerta)
class HistorialAlertaAdmin(admin.ModelAdmin):
    """Admin para el historial de alertas"""
    
    list_display = (
        'fecha',
        'alerta_link',
        'accion_badge',
        'usuario',
        'descripcion_corta',
    )
    
    list_filter = (
        'accion',
        ('fecha', admin.DateFieldListFilter),
        'usuario',
    )
    
    search_fields = (
        'alerta__titulo',
        'accion',
        'descripcion',
    )
    
    readonly_fields = (
        'id',
        'alerta',
        'accion',
        'descripcion',
        'usuario',
        'fecha',
        'datos_adicionales',
    )
    
    def has_add_permission(self, request):
        """No permite agregar manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permite eliminar (auditoría)"""
        return False
    
    @admin.display(description='Alerta')
    def alerta_link(self, obj):
        """Link a la alerta"""
        url = reverse('admin:stock_alert_system_alertastock_change', args=[obj.alerta.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.alerta.titulo[:40] + '...' if len(obj.alerta.titulo) > 40 else obj.alerta.titulo
        )
    
    @admin.display(description='Acción')
    def accion_badge(self, obj):
        """Badge de la acción"""
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            obj.accion
        )
    
    @admin.display(description='Descripción')
    def descripcion_corta(self, obj):
        """Descripción truncada"""
        max_len = 60
        return obj.descripcion[:max_len] + '...' if len(obj.descripcion) > max_len else obj.descripcion


# ============================================================================
# HISTORIAL DE ESTADOS
# ============================================================================

@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    """Admin para el historial de cambios de estado"""
    
    list_display = (
        'fecha_cambio',
        'producto_link',
        'cambio_estado_visual',
        'cambio_stock_visual',
        'tipo_inventario',
        'motivo_badge',
    )
    
    list_filter = (
        'estado_nuevo',
        'tipo_inventario',
        ('fecha_cambio', admin.DateFieldListFilter),
        'motivo_cambio',
    )
    
    search_fields = (
        'producto__nombre',
        'producto__codigo',
        'motivo_cambio',
    )
    
    readonly_fields = (
        'id',
        'producto',
        'estado_stock',
        'estado_anterior',
        'estado_nuevo',
        'tipo_inventario',
        'stock_anterior',
        'stock_nuevo',
        'motivo_cambio',
        'fecha_cambio',
    )
    
    date_hierarchy = 'fecha_cambio'
    
    def has_add_permission(self, request):
        """No permite agregar manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permite eliminar (auditoría)"""
        return False
    
    @admin.display(description='Producto', ordering='producto__nombre')
    def producto_link(self, obj):
        """Link al producto"""
        url = reverse('admin:inventory_management_producto_change', args=[obj.producto.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.producto.nombre
        )
    
    @admin.display(description='Cambio de Estado')
    def cambio_estado_visual(self, obj):
        """Muestra el cambio de estado visualmente"""
        colores = {
            'NORMAL': '#28a745',
            'BAJO': '#ffc107',
            'CRITICO': '#dc3545',
            'AGOTADO': '#343a40',
        }
        
        color_anterior = colores.get(obj.estado_anterior, '#6c757d')
        color_nuevo = colores.get(obj.estado_nuevo, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span> '
            '→ '
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color_anterior,
            obj.estado_anterior,
            color_nuevo,
            obj.estado_nuevo
        )
    
    @admin.display(description='Cambio de Stock')
    def cambio_stock_visual(self, obj):
        """Muestra el cambio de stock visualmente"""
        diff = obj.stock_nuevo - obj.stock_anterior
        color = '#28a745' if diff > 0 else '#dc3545'
        simbolo = '+' if diff > 0 else ''
        
        return format_html(
            '<span style="font-weight: bold;">{:.2f}</span> → '
            '<span style="font-weight: bold;">{:.2f}</span> '
            '<span style="color: {}; font-weight: bold;">({}{:.2f})</span>',
            obj.stock_anterior,
            obj.stock_nuevo,
            color,
            simbolo,
            diff
        )
    
    @admin.display(description='Motivo')
    def motivo_badge(self, obj):
        """Badge del motivo del cambio"""
        if not obj.motivo_cambio:
            return '-'
        
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            obj.motivo_cambio
        )
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('producto', 'estado_stock')