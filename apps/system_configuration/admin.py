# apps/system_configuration/admin.py

"""
Admin para el módulo de configuración del sistema
✅ CORREGIDO: Referencias a iva_default → porcentaje_iva + iva_activo
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Sum
from datetime import timedelta
from django.utils import timezone

from .models import (
    ConfiguracionSistema, ParametroSistema, RegistroBackup,
    LogConfiguracion, HealthCheck
)


# ============================================================================
# HELPERS
# ============================================================================

def format_bytes(bytes_value):
    """Convierte bytes a formato legible"""
    if bytes_value is None:
        return '0 B'
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


# ============================================================================
# ADMIN: Configuración del Sistema
# ============================================================================

@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    """Admin para la configuración única del sistema"""
    
    # ✅ CORREGIDO: iva_default → porcentaje_iva + iva_activo
    list_display = [
        'nombre_empresa', 'ruc_empresa', 'logo_preview', 
        'porcentaje_iva', 'iva_activo', 'moneda', 'ultima_actualizacion'
    ]
    
    fieldsets = (
        ('🏢 Información de la Empresa', {
            'fields': (
                'nombre_empresa', 'ruc_empresa', 'direccion_empresa',
                'telefono_empresa', 'email_empresa', 'sitio_web', 
                'logo_empresa', 'logo_preview_large'
            ),
            'description': 'Información básica de la empresa y logo corporativo'
        }),
        ('📦 Configuración de Inventario', {
            'fields': (
                'prefijo_codigo_quintal', 'prefijo_codigo_producto',
                'longitud_codigo_secuencial', 'umbral_stock_critico_porcentaje',
                'umbral_stock_bajo_porcentaje', 'stock_minimo_default',
                'dias_alerta_vencimiento', 'peso_minimo_quintal_critico'
            ),
            'classes': ('collapse',),
            'description': 'Parámetros para el control de inventario'
        }),
        ('💰 Configuración de Ventas e IVA', {
            'fields': (
                'prefijo_numero_factura', 'prefijo_numero_venta',
                # ✅ CORREGIDO: iva_default → iva_activo + porcentaje_iva
                'iva_activo', 'porcentaje_iva',
                'max_descuento_sin_autorizacion',
                'permitir_ventas_credito', 'dias_credito_default'
            ),
            'description': '⚠️ El IVA configurado aquí se aplicará automáticamente en todas las ventas del sistema. Use "IVA Activo" para activar/desactivar el cálculo.'
        }),
        ('💵 Configuración Financiera', {
            'fields': (
                'moneda', 'simbolo_moneda', 'decimales_moneda',
                'monto_inicial_caja', 'monto_fondo_caja_chica', 
                'alerta_diferencia_caja'
            ),
            'classes': ('collapse',),
            'description': 'Configuración monetaria y de cajas'
        }),
        ('📄 Facturación Electrónica', {
            'fields': (
                'facturacion_electronica_activa', 'ambiente_facturacion',
                'certificado_digital_path', 'clave_certificado'
            ),
            'classes': ('collapse',),
            'description': 'Configuración para facturación electrónica'
        }),
        ('📧 Notificaciones', {
            'fields': (
                'notificaciones_email_activas', 'email_notificaciones',
                'emails_adicionales', 'notificar_stock_bajo', 
                'notificar_vencimientos', 'notificar_cierre_caja'
            ),
            'classes': ('collapse',),
            'description': 'Configuración de alertas y notificaciones por email'
        }),
        ('💾 Backups', {
            'fields': (
                'backup_automatico_activo', 'frecuencia_backup',
                'hora_backup', 'dias_retencion_backup', 'ruta_backup'
            ),
            'classes': ('collapse',),
            'description': 'Configuración de respaldos automáticos'
        }),
        ('🔧 Sistema', {
            'fields': (
                'version_sistema', 'mantenimiento_activo', 
                'mensaje_mantenimiento', 'activar_logs_detallados', 
                'dias_retencion_logs'
            ),
            'classes': ('collapse',),
            'description': 'Configuración general del sistema'
        }),
        ('🔒 Seguridad', {
            'fields': (
                'timeout_sesion', 'intentos_login_maximos', 
                'tiempo_bloqueo_cuenta'
            ),
            'classes': ('collapse',),
            'description': 'Parámetros de seguridad y autenticación'
        }),
        ('🎨 Interfaz', {
            'fields': (
                'tema_interfaz', 'idioma', 'zona_horaria', 
                'formato_fecha', 'formato_hora'
            ),
            'classes': ('collapse',),
            'description': 'Personalización de la interfaz de usuario'
        }),
        ('📱 Módulos Activos', {
            'fields': (
                'modulo_inventario_activo', 'modulo_ventas_activo',
                'modulo_financiero_activo', 'modulo_reportes_activo', 
                'modulo_alertas_activo'
            ),
            'classes': ('collapse',),
            'description': 'Activar o desactivar módulos del sistema'
        }),
        ('👤 Auditoría', {
            'fields': (
                'fecha_creacion', 'fecha_actualizacion', 'actualizado_por'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'version_sistema', 'fecha_creacion', 'fecha_actualizacion',
        'logo_preview_large'
    ]
    
    def logo_preview(self, obj):
        """Muestra una vista previa pequeña del logo"""
        if obj.logo_empresa:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px; object-fit: contain; border-radius: 4px; border: 1px solid #ddd;" />',
                obj.logo_empresa.url
            )
        return format_html('<span style="color: #999; font-style: italic;">Sin logo</span>')
    logo_preview.short_description = 'Logo'
    
    def logo_preview_large(self, obj):
        """Muestra una vista previa grande del logo en el formulario"""
        if obj.logo_empresa:
            return format_html(
                '<div style="text-align: center; padding: 20px; background: #f5f5f5; border-radius: 8px;">'
                '<img src="{}" style="max-height: 200px; max-width: 300px; object-fit: contain;" />'
                '<p style="margin-top: 10px; color: #666; font-size: 12px;">Archivo: {}</p>'
                '</div>',
                obj.logo_empresa.url,
                obj.logo_empresa.name
            )
        return format_html(
            '<div style="text-align: center; padding: 40px; background: #f5f5f5; border-radius: 8px; color: #999;">'
            '<i style="font-size: 48px;">📷</i>'
            '<p>No hay logo configurado</p>'
            '</div>'
        )
    logo_preview_large.short_description = 'Vista Previa del Logo'
    
    def ultima_actualizacion(self, obj):
        """Muestra cuándo fue la última actualización"""
        if obj.fecha_actualizacion:
            delta = timezone.now() - obj.fecha_actualizacion
            if delta.days == 0:
                return format_html('<span style="color: green;">Hoy</span>')
            elif delta.days == 1:
                return format_html('<span style="color: orange;">Ayer</span>')
            else:
                return format_html(
                    '<span style="color: gray;">Hace {} días</span>',
                    delta.days
                )
        return '-'
    ultima_actualizacion.short_description = 'Última Actualización'
    
    def has_add_permission(self, request):
        """Solo puede existir una configuración (Singleton)"""
        return ConfiguracionSistema.objects.count() == 0
    
    def has_delete_permission(self, request, obj=None):
        """No se puede eliminar la configuración"""
        return False
    
    class Media:
        css = {
            'all': ('admin/css/configuracion-sistema.css',)
        }
        js = ('admin/js/configuracion-sistema.js',)


# ============================================================================
# ADMIN: Parámetros del Sistema
# ============================================================================

@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    """Admin para parámetros personalizados del sistema"""
    
    list_display = [
        'clave', 'modulo', 'tipo_dato_badge', 'valor_display', 
        'descripcion_corta', 'activo', 'fecha_actualizacion'
    ]
    list_filter = ['modulo', 'tipo_dato', 'activo', 'grupo', 'fecha_creacion']
    search_fields = ['clave', 'nombre', 'descripcion', 'valor']
    ordering = ['modulo', 'grupo', 'orden', 'nombre']
    list_editable = ['activo']
    list_per_page = 50
    
    fieldsets = (
        ('🔑 Identificación', {
            'fields': ('modulo', 'clave', 'nombre', 'descripcion')
        }),
        ('📝 Valor', {
            'fields': ('tipo_dato', 'valor', 'valor_default'),
            'description': 'Configure el valor según el tipo de dato seleccionado'
        }),
        ('✅ Validación', {
            'fields': ('requerido', 'validacion_regex'),
            'classes': ('collapse',)
        }),
        ('📁 Organización', {
            'fields': ('grupo', 'orden'),
            'classes': ('collapse',)
        }),
        ('⚙️ Configuración', {
            'fields': ('activo', 'editable'),
            'classes': ('collapse',)
        }),
        ('👤 Auditoría', {
            'fields': ('fecha_creacion', 'actualizado_por', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'actualizado_por']
    
    def tipo_dato_badge(self, obj):
        """Muestra el tipo de dato con badge estilizado"""
        tipos_config = {
            'STRING': ('badge-primary', 'bi-fonts', 'TEXTO'),
            'INTEGER': ('badge-success', 'bi-123', 'ENTERO'),
            'DECIMAL': ('badge-success', 'bi-calculator', 'DECIMAL'),
            'BOOLEAN': ('badge-info', 'bi-toggle-on', 'BOOLEAN'),
            'JSON': ('badge-primary', 'bi-braces', 'JSON'),
            'DATE': ('badge-warning', 'bi-calendar-date', 'FECHA'),
            'DATETIME': ('badge-warning', 'bi-calendar-event', 'FECHA/HORA'),
        }
        
        badge_class, icono, texto = tipos_config.get(
            obj.tipo_dato, 
            ('badge-secondary', 'bi-question-circle', obj.tipo_dato)
        )
        
        return format_html(
            '<span class="badge-admin {}">'
            '<i class="bi {}"></i> {}'
            '</span>',
            badge_class, icono, texto
        )
    tipo_dato_badge.short_description = 'Tipo de Dato'
    tipo_dato_badge.admin_order_field = 'tipo_dato'
    
    def valor_display(self, obj):
        """Muestra el valor configurado con estilo mejorado"""
        valor = obj.get_valor()
        
        if valor is None or valor == '':
            return format_html(
                '<span class="badge-admin badge-secondary">'
                '<i class="bi bi-dash-circle"></i> Sin valor'
                '</span>'
            )
        
        try:
            if obj.tipo_dato == 'JSON':
                valor_str = str(valor)[:50]
                return format_html(
                    '<code class="code-badge">{}</code>',
                    valor_str + ('...' if len(str(valor)) > 50 else '')
                )
            
            elif obj.tipo_dato == 'BOOLEAN':
                return format_html(
                    '<span class="badge-admin badge-{}">'
                    '<i class="bi bi-{}"></i> {}'
                    '</span>',
                    'success' if valor else 'danger',
                    'check-circle-fill' if valor else 'x-circle-fill',
                    'Sí' if valor else 'No'
                )
            
            elif obj.tipo_dato in ('INTEGER', 'DECIMAL'):
                return format_html(
                    '<span class="code-badge">'
                    '<i class="bi bi-hash"></i> {}'
                    '</span>',
                    valor
                )
            
            elif obj.tipo_dato == 'DATE':
                fecha_formateada = valor.strftime('%d/%m/%Y') if hasattr(valor, 'strftime') else str(valor)
                return format_html(
                    '<span class="badge-admin badge-info">'
                    '<i class="bi bi-calendar-date"></i> {}'
                    '</span>',
                    fecha_formateada
                )
            
            elif obj.tipo_dato == 'DATETIME':
                fecha_formateada = valor.strftime('%d/%m/%Y %H:%M') if hasattr(valor, 'strftime') else str(valor)
                return format_html(
                    '<span class="badge-admin badge-info">'
                    '<i class="bi bi-calendar-event"></i> {}'
                    '</span>',
                    fecha_formateada
                )
            
            else:  # STRING
                valor_str = str(valor)[:50]
                return format_html(
                    '<span>{}</span>',
                    valor_str + ('...' if len(str(valor)) > 50 else '')
                )
        except Exception as e:
            return format_html(
                '<span class="badge-admin badge-danger">'
                '<i class="bi bi-exclamation-triangle"></i> Error'
                '</span>'
            )
    valor_display.short_description = 'Valor Actual'
    
    def descripcion_corta(self, obj):
        """Muestra una descripción corta con tooltip"""
        texto = obj.descripcion or obj.nombre
        if len(texto) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                texto,
                f"{texto[:50]}..."
            )
        return texto
    descripcion_corta.short_description = 'Descripción'
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo registrando quién lo modificó"""
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# ADMIN: Registro de Backups
# ============================================================================

@admin.register(RegistroBackup)
class RegistroBackupAdmin(admin.ModelAdmin):
    """Admin para registros de backups"""
    
    list_display = [
        'fecha_inicio', 'tipo_backup_badge', 'estado_badge',
        'tamano_display', 'tiempo_duracion'
    ]
    list_filter = ['tipo_backup', 'estado', 'fecha_inicio']
    search_fields = ['nombre_archivo', 'ruta_archivo', 'mensaje_error']
    ordering = ['-fecha_inicio']
    date_hierarchy = 'fecha_inicio'
    list_per_page = 50
    
    fieldsets = (
        ('📋 Información del Backup', {
            'fields': ('tipo_backup', 'nombre_archivo', 'ruta_archivo')
        }),
        ('📊 Detalles', {
            'fields': (
                'tamaño_bytes', 'estado', 'fecha_inicio',
                'fecha_finalizacion', 'duracion_segundos', 'mensaje_error'
            )
        }),
        ('👤 Usuario', {
            'fields': ('usuario',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'nombre_archivo', 'ruta_archivo', 'tamaño_bytes',
        'estado', 'fecha_inicio', 'fecha_finalizacion', 
        'duracion_segundos', 'mensaje_error', 'usuario'
    ]
    
    def tipo_backup_badge(self, obj):
        """Muestra el tipo de backup con badge"""
        tipos_config = {
            'COMPLETO': ('#007bff', '💾', 'COMPLETO'),
            'INCREMENTAL': ('#28a745', '📦', 'INCREMENTAL'),
            'MANUAL': ('#ffc107', '👤', 'MANUAL'),
        }
        color, icono, texto = tipos_config.get(obj.tipo_backup, ('#000', '●', obj.tipo_backup))
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icono, texto
        )
    tipo_backup_badge.short_description = 'Tipo'
    tipo_backup_badge.admin_order_field = 'tipo_backup'
    
    def estado_badge(self, obj):
        """Muestra el estado del backup con badge"""
        estados_config = {
            'EXITOSO': ('#28a745', '✓', 'EXITOSO'),
            'EN_PROCESO': ('#ffc107', '⏳', 'EN PROCESO'),
            'FALLIDO': ('#dc3545', '✗', 'FALLIDO'),
        }
        color, icono, texto = estados_config.get(obj.estado, ('#000', '●', obj.estado))
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icono, texto
        )
    estado_badge.short_description = 'Estado'
    estado_badge.admin_order_field = 'estado'
    
    def tamano_display(self, obj):
        """Muestra el tamaño del archivo de forma legible"""
        if obj.tamaño_bytes:
            return format_bytes(obj.tamaño_bytes)
        return '-'
    tamano_display.short_description = 'Tamaño'
    tamano_display.admin_order_field = 'tamaño_bytes'
    
    def tiempo_duracion(self, obj):
        """Calcula y muestra la duración del backup"""
        if obj.duracion_segundos:
            segundos = obj.duracion_segundos
            
            if segundos < 60:
                return f"{segundos}s"
            elif segundos < 3600:
                minutos = segundos // 60
                return f"{minutos}m {segundos % 60}s"
            else:
                horas = segundos // 3600
                minutos = (segundos % 3600) // 60
                return f"{horas}h {minutos}m"
        elif obj.fecha_inicio and obj.fecha_finalizacion:
            duracion = obj.fecha_finalizacion - obj.fecha_inicio
            segundos = int(duracion.total_seconds())
            
            if segundos < 60:
                return f"{segundos}s"
            elif segundos < 3600:
                minutos = segundos // 60
                return f"{minutos}m {segundos % 60}s"
            else:
                horas = segundos // 3600
                minutos = (segundos % 3600) // 60
                return f"{horas}h {minutos}m"
        return '-'
    tiempo_duracion.short_description = 'Duración'
    
    def has_add_permission(self, request):
        """Los backups se crean desde el proceso automático o manual"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar backups desde el admin"""
        return False


# ============================================================================
# ADMIN: Logs de Configuración
# ============================================================================

@admin.register(LogConfiguracion)
class LogConfiguracionAdmin(admin.ModelAdmin):
    """Admin para logs de cambios de configuración"""
    
    list_display = [
        'fecha_cambio', 'tabla', 'tipo_cambio_badge',
        'campo_modificado', 'usuario', 'descripcion_corta'
    ]
    list_filter = ['tipo_cambio', 'tabla', 'fecha_cambio']
    search_fields = [
        'tabla', 'campo_modificado', 'descripcion', 
        'usuario__username', 'usuario__email'
    ]
    ordering = ['-fecha_cambio']
    date_hierarchy = 'fecha_cambio'
    list_per_page = 100
    
    fieldsets = (
        ('📋 Información del Cambio', {
            'fields': ('tabla', 'registro_id', 'tipo_cambio', 'campo_modificado')
        }),
        ('🔄 Valores', {
            'fields': ('valor_anterior', 'valor_nuevo')
        }),
        ('📝 Detalles', {
            'fields': ('descripcion', 'ip_address')
        }),
        ('👤 Usuario y Fecha', {
            'fields': ('usuario', 'fecha_cambio')
        }),
    )
    
    readonly_fields = [
        'tabla', 'registro_id', 'tipo_cambio', 'campo_modificado',
        'valor_anterior', 'valor_nuevo', 'descripcion', 'ip_address',
        'usuario', 'fecha_cambio'
    ]
    
    def tipo_cambio_badge(self, obj):
        """Muestra el tipo de cambio con badge"""
        tipos_config = {
            'CREACION': ('#28a745', '➕', 'CREACIÓN'),
            'MODIFICACION': ('#ffc107', '✏️', 'MODIFICACIÓN'),
            'ELIMINACION': ('#dc3545', '🗑️', 'ELIMINACIÓN'),
        }
        color, icono, texto = tipos_config.get(obj.tipo_cambio, ('#000', '●', obj.tipo_cambio))
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icono, texto
        )
    tipo_cambio_badge.short_description = 'Tipo'
    tipo_cambio_badge.admin_order_field = 'tipo_cambio'
    
    def descripcion_corta(self, obj):
        """Muestra una descripción corta"""
        if len(obj.descripcion) > 80:
            return format_html(
                '<span title="{}">{}</span>',
                obj.descripcion,
                f"{obj.descripcion[:80]}..."
            )
        return obj.descripcion
    descripcion_corta.short_description = 'Descripción'
    
    def has_add_permission(self, request):
        """Los logs se crean automáticamente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar logs desde el admin"""
        return False


# ============================================================================
# ADMIN: Health Check
# ============================================================================

@admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    """Admin para health checks del sistema"""
    
    list_display = [
        'fecha_check', 'estado_badge', 'componentes_status',
        'disco_status', 'memoria_status'
    ]
    list_filter = ['estado_general', 'fecha_check']
    ordering = ['-fecha_check']
    date_hierarchy = 'fecha_check'
    list_per_page = 50
    
    fieldsets = (
        ('🏥 Estado General', {
            'fields': ('estado_general', 'fecha_check')
        }),
        ('🔧 Componentes', {
            'fields': (
                'base_datos_ok', 'redis_ok', 'celery_ok',
                'disco_ok', 'memoria_ok'
            )
        }),
        ('📊 Métricas', {
            'fields': (
                'espacio_disco_libre_gb', 'uso_memoria_porcentaje',
                'tiempo_respuesta_db_ms'
            )
        }),
        ('ℹ️ Detalles', {
            'fields': ('detalles', 'errores', 'advertencias'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'estado_general', 'base_datos_ok', 'redis_ok', 'celery_ok',
        'disco_ok', 'memoria_ok', 'espacio_disco_libre_gb',
        'uso_memoria_porcentaje', 'tiempo_respuesta_db_ms',
        'detalles', 'errores', 'advertencias', 'fecha_check'
    ]
    
    def estado_badge(self, obj):
        """Muestra el estado general con badge"""
        estados_config = {
            'SALUDABLE': ('#28a745', '✓', 'SALUDABLE'),
            'ADVERTENCIA': ('#ffc107', '⚠️', 'ADVERTENCIA'),
            'CRITICO': ('#dc3545', '✗', 'CRÍTICO'),
        }
        color, icono, texto = estados_config.get(obj.estado_general, ('#000', '●', obj.estado_general))
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icono, texto
        )
    estado_badge.short_description = 'Estado'
    estado_badge.admin_order_field = 'estado_general'
    
    def componentes_status(self, obj):
        """Muestra el estado de los componentes principales"""
        componentes = [
            ('BD', obj.base_datos_ok),
            ('Redis', obj.redis_ok),
            ('Celery', obj.celery_ok),
        ]
        html = ''
        for nombre, estado in componentes:
            if estado:
                html += f'<span style="color: green; margin-right: 10px;">✓ {nombre}</span>'
            else:
                html += f'<span style="color: red; margin-right: 10px;">✗ {nombre}</span>'
        return format_html(html)
    componentes_status.short_description = 'Componentes'
    
    def disco_status(self, obj):
        """Muestra el estado del disco"""
        if obj.espacio_disco_libre_gb:
            try:
                # Convertir explícitamente a float
                espacio_libre = float(obj.espacio_disco_libre_gb)
            
                # Determinar el color según el espacio libre
                if espacio_libre > 10:
                    color = 'green'
                elif espacio_libre > 5:
                    color = 'orange'
                else:
                    color = 'red'
            
                # Formatear el número PRIMERO, luego pasarlo como string
                espacio_formateado = f"{espacio_libre:.2f}"
            
                return format_html(
                    '<span style="color: {};">{} GB libres</span>',
                    color, 
                    espacio_formateado
                )
            except (ValueError, TypeError):
                return '-'
        return '-'
    disco_status.short_description = 'Disco'
    
    def memoria_status(self, obj):
        """Muestra el uso de memoria con badge estilizado"""
        if obj.uso_memoria_porcentaje:
            try:
                uso = float(obj.uso_memoria_porcentaje)
            
                # Determinar badge según el porcentaje de uso
                if uso < 70:
                    badge_class = 'badge-success'
                    icon = 'bi-memory'
                elif uso < 85:
                    badge_class = 'badge-warning'
                    icon = 'bi-exclamation-circle'
                else:
                    badge_class = 'badge-danger'
                    icon = 'bi-exclamation-triangle-fill'
            
                # Formatear primero
                uso_formateado = f"{uso:.1f}"
            
                return format_html(
                    '<span class="badge-admin {}">'
                    '<i class="bi {}"></i> {}% usado'
                    '</span>',
                    badge_class,
                    icon,
                    uso_formateado
                )
            except (ValueError, TypeError):
                return format_html('<span class="badge-admin badge-secondary">N/A</span>')
        return '-'
    memoria_status.short_description = 'Memoria'   
    def has_add_permission(self, request):
        """Los health checks se crean automáticamente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminar checks antiguos"""
        return True


# ============================================================================
# CONFIGURACIÓN DEL ADMIN SITE
# ============================================================================

# Personalizar títulos del admin
admin.site.site_header = 'CommerceBox - Administración del Sistema'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Panel de Configuración del Sistema'