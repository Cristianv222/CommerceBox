# apps/hardware_integration/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import (
    Impresora, PlantillaImpresion, ConfiguracionCodigoBarras,
    GavetaDinero, RegistroImpresion, EscanerCodigoBarras
)
from .printers.printer_service import PrinterService
from .printers.cash_drawer_service import CashDrawerService
from django.utils import timezone


# ========================
# INLINES
# ========================

class GavetaDineroInline(admin.TabularInline):
    model = GavetaDinero
    extra = 0
    fields = ('nombre', 'ubicacion', 'activa', 'estado')
    readonly_fields = ('estado',)


class PlantillaImpresionInline(admin.TabularInline):
    model = PlantillaImpresion
    extra = 0
    fields = ('nombre', 'tipo_documento', 'activa', 'es_predeterminada')
    readonly_fields = ('es_predeterminada',)


# ========================
# ACCIONES PERSONALIZADAS
# ========================

def test_conexion_impresoras(modeladmin, request, queryset):
    success_count = 0
    for impresora in queryset:
        try:
            success, msg = PrinterService.test_connection(impresora)
            if success:
                impresora.estado = 'ACTIVA'
                success_count += 1
            else:
                impresora.estado = 'ERROR'
            impresora.save(update_fields=['estado'])
        except Exception as e:
            impresora.estado = 'ERROR'
            impresora.save(update_fields=['estado'])
            modeladmin.message_user(request, f"Error en {impresora.nombre}: {str(e)}", messages.ERROR)
    if success_count > 0:
        modeladmin.message_user(request, f"✅ {success_count} impresoras conectadas exitosamente.", messages.SUCCESS)
test_conexion_impresoras.short_description = "🔍 Probar conexión seleccionadas"


def reiniciar_contador_impresoras(modeladmin, request, queryset):
    for impresora in queryset:
        impresora.contador_impresiones = 0
        impresora.fecha_ultimo_mantenimiento = timezone.now()
        impresora.save(update_fields=['contador_impresiones', 'fecha_ultimo_mantenimiento'])
    modeladmin.message_user(request, "🔄 Contadores reiniciados.", messages.INFO)
reiniciar_contador_impresoras.short_description = "🔄 Reiniciar contador de impresiones"


def abrir_gavetas_seleccionadas(modeladmin, request, queryset):
    success_count = 0
    for gaveta in queryset:
        if CashDrawerService.abrir_gaveta(gaveta, request.user):
            success_count += 1
    if success_count > 0:
        modeladmin.message_user(request, f"🔓 {success_count} gavetas abiertas.", messages.SUCCESS)
    else:
        modeladmin.message_user(request, "❌ No se pudo abrir ninguna gaveta.", messages.ERROR)
abrir_gavetas_seleccionadas.short_description = "🔓 Abrir gavetas seleccionadas"


# ========================
# ADMIN CLASSES
# ========================

@admin.register(Impresora)
class ImpresoraAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'marca', 'modelo', 'tipo_impresora_display',
        'estado_badge', 'ubicacion', 'contador_impresiones', 'ultima_prueba'
    ]
    list_filter = [
        'tipo_impresora', 'estado', 'ubicacion', 'marca',
        'es_principal_tickets', 'es_principal_facturas', 'es_principal_etiquetas'
    ]
    search_fields = ['nombre', 'codigo', 'marca', 'modelo', 'numero_serie']
    readonly_fields = [
        'id', 'codigo', 'fecha_instalacion', 'fecha_ultima_prueba',
        'fecha_ultimo_mantenimiento', 'contador_impresiones'
    ]
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'marca', 'modelo', 'numero_serie')
        }),
        ('Tipo y Conexión', {
            'fields': ('tipo_impresora', 'tipo_conexion', 'protocolo')
        }),
        ('Configuración de Conexión', {
            'fields': (
                ('direccion_ip', 'puerto_red', 'mac_address'),
                ('puerto_usb', 'vid_usb', 'pid_usb'),
                ('puerto_serial', 'baudrate'),
                'nombre_driver'
            )
        }),
        ('Papel y Etiquetas', {
            'fields': (
                ('ancho_papel', 'largo_maximo'),
                ('ancho_etiqueta', 'alto_etiqueta', 'gap_etiquetas')
            )
        }),
        ('Capacidades', {
            'fields': (
                'soporta_corte_automatico', 'soporta_corte_parcial',
                'soporta_codigo_barras', 'soporta_qr', 'soporta_imagenes'
            )
        }),
        ('Gaveta de Dinero', {
            'fields': ('tiene_gaveta', 'pin_gaveta')
        }),
        ('Estado y Ubicación', {
            'fields': ('estado', 'ubicacion', 'notas')
        }),
        ('Uso Predeterminado', {
            'fields': (
                'es_principal_tickets',
                'es_principal_facturas',
                'es_principal_etiquetas'
            )
        }),
        ('Auditoría', {
            'fields': (
                'fecha_instalacion', 'fecha_ultima_prueba',
                'fecha_ultimo_mantenimiento', 'contador_impresiones'
            )
        }),
        ('Configuración Avanzada', {
            'fields': ('configuracion_extra',),
            'classes': ('collapse',)
        }),
    )
    inlines = [GavetaDineroInline, PlantillaImpresionInline]
    actions = [test_conexion_impresoras, reiniciar_contador_impresoras]

    def tipo_impresora_display(self, obj):
        return obj.get_tipo_impresora_display()
    tipo_impresora_display.short_description = 'Tipo'

    def estado_badge(self, obj):
        badges = {
            'ACTIVA': '<span style="color: green;">🟢 Activa</span>',
            'INACTIVA': '<span style="color: orange;">🟡 Inactiva</span>',
            'ERROR': '<span style="color: red;">🔴 Error</span>',
            'MANTENIMIENTO': '<span style="color: blue;">🔧 Mantenimiento</span>',
        }
        return format_html(badges.get(obj.estado, obj.estado))
    estado_badge.short_description = 'Estado'

    def ultima_prueba(self, obj):
        return obj.fecha_ultima_prueba.strftime('%d/%m/%Y %H:%M') if obj.fecha_ultima_prueba else '-'
    ultima_prueba.short_description = 'Última Prueba'


@admin.register(GavetaDinero)
class GavetaDineroAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'ubicacion', 'tipo_conexion', 'impresora', 'estado', 'activa'
    ]
    list_filter = ['tipo_conexion', 'estado', 'activa', 'requiere_autorizacion']
    search_fields = ['nombre', 'codigo', 'ubicacion']
    readonly_fields = [
        'id', 'codigo', 'contador_aperturas', 'fecha_ultima_apertura',
        'usuario_ultima_apertura'
    ]
    actions = [abrir_gavetas_seleccionadas]


@admin.register(PlantillaImpresion)
class PlantillaImpresionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_documento', 'formato', 'activa', 'es_predeterminada', 'impresora']
    list_filter = ['tipo_documento', 'formato', 'activa', 'es_predeterminada']
    search_fields = ['nombre', 'codigo']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    list_editable = ['activa', 'es_predeterminada']


@admin.register(ConfiguracionCodigoBarras)
class ConfiguracionCodigoBarrasAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_codigo', 'prefijo', 'sufijo', 'activa', 'es_predeterminada']
    list_filter = ['tipo_codigo', 'activa', 'es_predeterminada']
    search_fields = ['nombre']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'ultimo_numero']
    list_editable = ['activa', 'es_predeterminada']


@admin.register(RegistroImpresion)
class RegistroImpresionAdmin(admin.ModelAdmin):
    list_display = ['tipo_documento', 'estado_badge', 'impresora', 'venta', 'usuario', 'fecha_impresion_short']
    list_filter = ['tipo_documento', 'estado', 'impresora', 'fecha_impresion']
    search_fields = ['numero_documento', 'contenido_resumen']
    readonly_fields = [f.name for f in RegistroImpresion._meta.fields]
    ordering = ['-fecha_impresion']

    def has_add_permission(self, request):
        return False

    def estado_badge(self, obj):
        badges = {
            'EXITOSO': '<span style="color: green;">✅ Exitoso</span>',
            'ERROR': '<span style="color: red;">❌ Error</span>',
            'CANCELADO': '<span style="color: orange;">⚠️ Cancelado</span>',
            'REINTENTANDO': '<span style="color: blue;">🔄 Reintentando</span>',
        }
        return format_html(badges.get(obj.estado, obj.estado))
    estado_badge.short_description = 'Estado'

    def fecha_impresion_short(self, obj):
        return obj.fecha_impresion.strftime('%d/%m/%Y %H:%M')
    fecha_impresion_short.short_description = 'Fecha'


@admin.register(EscanerCodigoBarras)
class EscanerCodigoBarrasAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'marca', 'modelo', 'tipo_escaner', 'modo_operacion', 'ubicacion', 'activo']
    list_filter = ['tipo_escaner', 'modo_operacion', 'activo', 'marca']
    search_fields = ['nombre', 'codigo', 'marca', 'modelo', 'numero_serie']
    readonly_fields = ['id', 'codigo', 'fecha_instalacion', 'contador_lecturas']
    list_editable = ['activo']