# apps/notifications/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    ConfiguracionNotificacion,
    TipoNotificacion,
    Notificacion,
    NotificacionProgramada,
    PlantillaNotificacion,
    LogNotificacion,
    PreferenciasNotificacion,
)


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

@admin.register(ConfiguracionNotificacion)
class ConfiguracionNotificacionAdmin(admin.ModelAdmin):
    """Administración de configuración global de notificaciones"""
    
    fieldsets = (
        ('Estado del Sistema', {
            'fields': ('notificaciones_activas',)
        }),
        ('Configuración de Email', {
            'fields': ('email_activo', 'email_host', 'email_puerto', 
                      'email_usuario', 'email_password', 'email_remitente'),
            'classes': ('collapse',)
        }),
        ('Configuración de SMS', {
            'fields': ('sms_activo', 'sms_proveedor', 'sms_api_key'),
            'classes': ('collapse',)
        }),
        ('Configuración de Push', {
            'fields': ('push_activo',),
            'classes': ('collapse',)
        }),
        ('Notificaciones de Stock', {
            'fields': ('notif_stock_critico', 'notif_stock_bajo', 
                      'notif_stock_agotado', 'notif_vencimiento_proximo'),
        }),
        ('Notificaciones de Ventas', {
            'fields': ('notif_venta_grande', 'notif_venta_grande_monto',
                      'notif_descuento_excesivo', 'notif_descuento_excesivo_porcentaje',
                      'notif_devolucion'),
        }),
        ('Notificaciones Financieras', {
            'fields': ('notif_caja_chica_baja', 'notif_caja_chica_limite',
                      'notif_diferencia_arqueo', 'notif_diferencia_arqueo_monto'),
        }),
        ('Notificaciones de Sistema', {
            'fields': ('notif_error_sistema', 'notif_backup_completado', 
                      'notif_hardware_error'),
        }),
        ('Destinatarios', {
            'fields': ('emails_administradores', 'emails_supervisores'),
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'actualizado_por'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    def has_add_permission(self, request):
        # Solo permitir un registro (Singleton)
        return not ConfiguracionNotificacion.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar la configuración
        return False


# ============================================================================
# TIPOS DE NOTIFICACIÓN
# ============================================================================

@admin.register(TipoNotificacion)
class TipoNotificacionAdmin(admin.ModelAdmin):
    """Administración de tipos de notificación"""
    
    list_display = ('codigo', 'nombre', 'categoria', 'prioridad_default', 
                   'requiere_accion', 'canales_envio', 'activo')
    list_filter = ('categoria', 'prioridad_default', 'activo', 
                  'enviar_email', 'enviar_push', 'enviar_sms')
    search_fields = ('codigo', 'nombre', 'descripcion')
    
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('categoria', 'prioridad_default', 'requiere_accion')
        }),
        ('Plantillas', {
            'fields': ('plantilla_titulo', 'plantilla_mensaje')
        }),
        ('Canales de Envío', {
            'fields': ('enviar_email', 'enviar_push', 'enviar_sms')
        }),
        ('Destinatarios', {
            'fields': ('roles_destinatarios',)
        }),
        ('Control', {
            'fields': ('activo',)
        }),
    )
    
    def canales_envio(self, obj):
        """Muestra los canales de envío activos"""
        canales = []
        if obj.enviar_email:
            canales.append('📧 Email')
        if obj.enviar_push:
            canales.append('📱 Push')
        if obj.enviar_sms:
            canales.append('💬 SMS')
        return ', '.join(canales) if canales else '❌ Ninguno'
    
    canales_envio.short_description = 'Canales'


# ============================================================================
# NOTIFICACIONES
# ============================================================================

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    """Administración de notificaciones"""
    
    list_display = ('titulo_formateado', 'usuario', 'tipo_notificacion', 
                   'prioridad_badge', 'estado_badge', 'fecha_creacion', 
                   'canales_enviados', 'acciones')
    list_filter = ('estado', 'prioridad', 'tipo_notificacion__categoria', 
                  'requiere_accion', 'enviada_email', 'fecha_creacion')
    search_fields = ('titulo', 'mensaje', 'usuario__nombres', 
                    'usuario__apellidos', 'usuario__email')
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('fecha_creacion', 'fecha_envio', 'fecha_lectura', 
                      'objeto_relacionado_link')
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('tipo_notificacion', 'usuario', 'titulo', 'mensaje')
        }),
        ('Clasificación', {
            'fields': ('prioridad', 'requiere_accion')
        }),
        ('Relación', {
            'fields': ('objeto_relacionado_link', 'url_accion'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('estado', 'accion_tomada')
        }),
        ('Canales', {
            'fields': ('enviada_web', 'enviada_email', 'enviada_push', 'enviada_sms')
        }),
        ('Datos Adicionales', {
            'fields': ('datos_adicionales',),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_envio', 'fecha_lectura', 
                      'fecha_expiracion'),
            'classes': ('collapse',)
        }),
        ('Error (si aplica)', {
            'fields': ('error_mensaje', 'intentos_envio'),
            'classes': ('collapse',)
        }),
    )
    
    def titulo_formateado(self, obj):
        """Muestra el título con emoji de prioridad"""
        return f"{obj.get_icono_prioridad()} {obj.titulo}"
    
    titulo_formateado.short_description = 'Título'
    
    def prioridad_badge(self, obj):
        """Muestra la prioridad con badge de color"""
        colores = {
            'BAJA': '#6c757d',
            'MEDIA': '#ffc107',
            'ALTA': '#fd7e14',
            'CRITICA': '#dc3545'
        }
        color = colores.get(obj.prioridad, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_prioridad_display()
        )
    
    prioridad_badge.short_description = 'Prioridad'
    
    def estado_badge(self, obj):
        """Muestra el estado con badge de color"""
        colores = {
            'PENDIENTE': '#6c757d',
            'ENVIADA': '#007bff',
            'LEIDA': '#28a745',
            'DESCARTADA': '#6c757d',
            'ERROR': '#dc3545'
        }
        color = colores.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_estado_display()
        )
    
    estado_badge.short_description = 'Estado'
    
    def canales_enviados(self, obj):
        """Muestra los canales por los que se envió"""
        canales = []
        if obj.enviada_web:
            canales.append('🌐')
        if obj.enviada_email:
            canales.append('📧')
        if obj.enviada_push:
            canales.append('📱')
        if obj.enviada_sms:
            canales.append('💬')
        return ' '.join(canales) if canales else '❌'
    
    canales_enviados.short_description = 'Enviado'
    
    def objeto_relacionado_link(self, obj):
        """Link al objeto relacionado"""
        if obj.objeto_relacionado:
            try:
                url = reverse(
                    f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                    args=[obj.object_id]
                )
                return format_html(
                    '<a href="{}">{}</a>',
                    url, str(obj.objeto_relacionado)
                )
            except:
                return str(obj.objeto_relacionado)
        return '-'
    
    objeto_relacionado_link.short_description = 'Objeto relacionado'
    
    def acciones(self, obj):
        """Botones de acción rápida"""
        botones = []
        
        if obj.estado in ['PENDIENTE', 'ENVIADA']:
            botones.append(format_html(
                '<a class="button" href="#" onclick="marcar_leida({}); return false;">Marcar Leída</a>',
                obj.id
            ))
        
        if obj.puede_reenviar():
            botones.append(format_html(
                '<a class="button" href="#" onclick="reenviar({}); return false;">Reenviar</a>',
                obj.id
            ))
        
        return format_html(' '.join(botones)) if botones else '-'
    
    acciones.short_description = 'Acciones'


# ============================================================================
# NOTIFICACIONES PROGRAMADAS
# ============================================================================

@admin.register(NotificacionProgramada)
class NotificacionProgramadaAdmin(admin.ModelAdmin):
    """Administración de notificaciones programadas"""
    
    list_display = ('nombre', 'tipo_notificacion', 'frecuencia', 
                   'proxima_ejecucion', 'activa_badge', 'ultima_ejecucion_info')
    list_filter = ('activa', 'frecuencia', 'tipo_notificacion__categoria')
    search_fields = ('nombre', 'descripcion')
    filter_horizontal = ('usuarios',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'tipo_notificacion')
        }),
        ('Programación', {
            'fields': ('frecuencia', 'fecha_proxima_ejecucion', 'hora_ejecucion')
        }),
        ('Destinatarios', {
            'fields': ('usuarios', 'roles')
        }),
        ('Contenido Personalizado', {
            'fields': ('titulo_personalizado', 'mensaje_personalizado'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('activa', 'ultima_ejecucion', 'total_ejecuciones')
        }),
    )
    
    readonly_fields = ('ultima_ejecucion', 'total_ejecuciones')
    
    def proxima_ejecucion(self, obj):
        """Muestra la próxima ejecución formateada"""
        if obj.fecha_proxima_ejecucion:
            ahora = timezone.now()
            if obj.fecha_proxima_ejecucion > ahora:
                return format_html(
                    '<span style="color: green;">⏰ {}</span>',
                    obj.fecha_proxima_ejecucion.strftime('%d/%m/%Y %H:%M')
                )
            else:
                return format_html(
                    '<span style="color: red;">⚠️ Vencida</span>'
                )
        return '-'
    
    proxima_ejecucion.short_description = 'Próxima Ejecución'
    
    def activa_badge(self, obj):
        """Badge del estado activo"""
        if obj.activa:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 8px; border-radius: 3px;">✓ Activa</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 3px 8px; border-radius: 3px;">✗ Inactiva</span>'
        )
    
    activa_badge.short_description = 'Estado'
    
    def ultima_ejecucion_info(self, obj):
        """Información de la última ejecución"""
        if obj.ultima_ejecucion:
            return f"{obj.ultima_ejecucion.strftime('%d/%m/%Y %H:%M')} ({obj.total_ejecuciones} veces)"
        return 'Nunca ejecutada'
    
    ultima_ejecucion_info.short_description = 'Última Ejecución'


# ============================================================================
# PLANTILLAS
# ============================================================================

@admin.register(PlantillaNotificacion)
class PlantillaNotificacionAdmin(admin.ModelAdmin):
    """Administración de plantillas"""
    
    list_display = ('codigo', 'nombre', 'tipo_plantilla', 'activa')
    list_filter = ('tipo_plantilla', 'activa')
    search_fields = ('codigo', 'nombre', 'descripcion')
    
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'descripcion', 'tipo_plantilla')
        }),
        ('Contenido', {
            'fields': ('asunto', 'cuerpo')
        }),
        ('Variables', {
            'fields': ('variables_disponibles',),
            'description': 'Variables que se pueden usar en la plantilla'
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
    )


# ============================================================================
# LOGS
# ============================================================================

@admin.register(LogNotificacion)
class LogNotificacionAdmin(admin.ModelAdmin):
    """Administración de logs"""
    
    list_display = ('notificacion_info', 'canal', 'resultado_badge', 
                   'destinatario', 'fecha_intento', 'tiempo_respuesta')
    list_filter = ('canal', 'resultado', 'fecha_intento')
    search_fields = ('destinatario', 'mensaje_error')
    date_hierarchy = 'fecha_intento'
    readonly_fields = ('notificacion', 'canal', 'resultado', 'destinatario', 
                      'mensaje_error', 'datos_respuesta', 'fecha_intento', 
                      'tiempo_respuesta')
    
    def has_add_permission(self, request):
        return False
    
    def notificacion_info(self, obj):
        """Información de la notificación"""
        return f"{obj.notificacion.titulo[:50]}..."
    
    notificacion_info.short_description = 'Notificación'
    
    def resultado_badge(self, obj):
        """Badge del resultado"""
        colores = {
            'EXITOSO': '#28a745',
            'ERROR': '#dc3545',
            'RECHAZADO': '#ffc107',
            'REBOTADO': '#fd7e14'
        }
        color = colores.get(obj.resultado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_resultado_display()
        )
    
    resultado_badge.short_description = 'Resultado'


# ============================================================================
# PREFERENCIAS
# ============================================================================

@admin.register(PreferenciasNotificacion)
class PreferenciasNotificacionAdmin(admin.ModelAdmin):
    """Administración de preferencias de usuario"""
    
    list_display = ('usuario', 'canales_activos', 'categorias_activas', 
                   'solo_prioridad_alta', 'no_molestar_info')
    list_filter = ('recibir_notificaciones_web', 'recibir_notificaciones_email',
                  'solo_prioridad_alta', 'no_molestar_activo')
    search_fields = ('usuario__nombres', 'usuario__apellidos', 'usuario__email')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Canales', {
            'fields': ('recibir_notificaciones_web', 'recibir_notificaciones_email',
                      'recibir_notificaciones_push', 'recibir_notificaciones_sms')
        }),
        ('Categorías', {
            'fields': ('notif_stock', 'notif_ventas', 'notif_financiero', 
                      'notif_sistema')
        }),
        ('Configuración Avanzada', {
            'fields': ('agrupar_notificaciones', 'solo_prioridad_alta')
        }),
        ('No Molestar', {
            'fields': ('no_molestar_activo', 'no_molestar_desde', 
                      'no_molestar_hasta')
        }),
    )
    
    def canales_activos(self, obj):
        """Canales activos"""
        canales = []
        if obj.recibir_notificaciones_web:
            canales.append('🌐 Web')
        if obj.recibir_notificaciones_email:
            canales.append('📧 Email')
        if obj.recibir_notificaciones_push:
            canales.append('📱 Push')
        if obj.recibir_notificaciones_sms:
            canales.append('💬 SMS')
        return ', '.join(canales) if canales else '❌ Ninguno'
    
    canales_activos.short_description = 'Canales'
    
    def categorias_activas(self, obj):
        """Categorías activas"""
        categorias = []
        if obj.notif_stock:
            categorias.append('📦 Stock')
        if obj.notif_ventas:
            categorias.append('🛒 Ventas')
        if obj.notif_financiero:
            categorias.append('💰 Financiero')
        if obj.notif_sistema:
            categorias.append('⚙️ Sistema')
        return ', '.join(categorias) if categorias else '❌ Ninguna'
    
    categorias_activas.short_description = 'Categorías'
    
    def no_molestar_info(self, obj):
        """Información de no molestar"""
        if obj.no_molestar_activo:
            return f"🔕 {obj.no_molestar_desde} - {obj.no_molestar_hasta}"
        return '✅ Disponible'
    
    no_molestar_info.short_description = 'No Molestar'