# apps/sales_management/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from decimal import Decimal

from .models import Cliente, Venta, DetalleVenta, Pago, Devolucion


# ============================================================================
# HELPERS
# ============================================================================

def format_currency(amount):
    """Helper para formatear montos como moneda"""
    if amount is None:
        return '$0.00'
    return f'${float(amount):,.2f}'


# ============================================================================
# INLINES
# ============================================================================

class DetalleVentaInline(admin.TabularInline):
    """Inline para detalles de venta"""
    model = DetalleVenta
    extra = 0
    readonly_fields = [
        'producto', 'peso_vendido', 'cantidad_unidades',
        'precio_por_unidad_peso', 'precio_unitario',
        'subtotal', 'descuento_monto', 'total'
    ]
    fields = [
        'producto', 'peso_vendido', 'cantidad_unidades',
        'subtotal', 'descuento_porcentaje', 'descuento_monto', 'total'
    ]
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    """Inline para pagos de venta"""
    model = Pago
    extra = 0
    readonly_fields = ['forma_pago', 'monto', 'numero_referencia', 'usuario', 'fecha_pago']
    fields = ['forma_pago', 'monto', 'numero_referencia', 'usuario', 'fecha_pago']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# ADMIN: Cliente
# ============================================================================

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        'numero_documento', 'nombre_completo_display', 'tipo_cliente',
        'telefono', 'credito_display', 'total_compras_display', 'activo'
    ]
    list_filter = ['tipo_cliente', 'activo', 'tipo_documento']
    search_fields = [
        'numero_documento', 'nombres', 'apellidos',
        'nombre_comercial', 'telefono', 'email'
    ]
    ordering = ['apellidos', 'nombres']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('tipo_documento', 'numero_documento')
        }),
        ('Información Personal', {
            'fields': ('nombres', 'apellidos', 'nombre_comercial')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email', 'direccion')
        }),
        ('Clasificación', {
            'fields': ('tipo_cliente', 'descuento_general')
        }),
        ('Crédito', {
            'fields': ('limite_credito', 'credito_disponible', 'dias_credito'),
            'classes': ('collapse',)
        }),
        ('Control', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'fecha_ultima_compra', 'total_compras'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_registro', 'fecha_ultima_compra', 'total_compras']
    
    def nombre_completo_display(self, obj):
        """Muestra el nombre completo del cliente"""
        if obj.nombre_comercial:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.nombre_comercial,
                obj.nombre_completo()
            )
        return obj.nombre_completo()
    nombre_completo_display.short_description = 'Cliente'
    
    def credito_display(self, obj):
        """Muestra el crédito disponible con código de colores"""
        if obj.limite_credito > 0:
            porcentaje = (obj.credito_disponible / obj.limite_credito) * 100
            if porcentaje > 50:
                color = 'green'
            elif porcentaje > 20:
                color = 'orange'
            else:
                color = 'red'
            
            disponible = format_currency(obj.credito_disponible)
            limite = format_currency(obj.limite_credito)
            
            return format_html(
                '<span style="color: {};">{} / {}</span>',
                color, disponible, limite
            )
        return '-'
    credito_display.short_description = 'Crédito Disponible'
    
    def total_compras_display(self, obj):
        """Muestra el total de compras acumuladas"""
        total = format_currency(obj.total_compras)
        return format_html('<strong>{}</strong>', total)
    total_compras_display.short_description = 'Total Compras'


# ============================================================================
# ADMIN: Venta
# ============================================================================

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_venta', 'fecha_venta', 'cliente_display',
        'vendedor', 'tipo_venta', 'total_display',
        'estado_display', 'estado_pago_display'
    ]
    list_filter = [
        'estado', 'tipo_venta', 'fecha_venta',
        'vendedor', 'factura_electronica_enviada'
    ]
    search_fields = [
        'numero_venta', 'numero_factura',
        'cliente__numero_documento', 'cliente__nombres',
        'cliente__apellidos'
    ]
    ordering = ['-fecha_venta']
    date_hierarchy = 'fecha_venta'
    
    fieldsets = (
        ('Información General', {
            'fields': ('numero_venta', 'numero_factura', 'fecha_venta')
        }),
        ('Cliente y Vendedor', {
            'fields': ('cliente', 'vendedor', 'tipo_venta', 'fecha_vencimiento')
        }),
        ('Montos', {
            'fields': ('subtotal', 'descuento', 'impuestos', 'total')
        }),
        ('Pagos', {
            'fields': ('monto_pagado', 'cambio')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
        }),
        ('Facturación Electrónica', {
            'fields': (
                'factura_electronica_enviada',
                'factura_electronica_clave',
                'factura_electronica_xml'
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('caja', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'numero_venta', 'fecha_creacion', 'fecha_actualizacion',
        'subtotal', 'total', 'monto_pagado', 'cambio'
    ]
    
    inlines = [DetalleVentaInline, PagoInline]
    
    def cliente_display(self, obj):
        """Muestra información del cliente"""
        if obj.cliente:
            return format_html(
                '{}<br><small>{}</small>',
                obj.cliente.nombre_completo(),
                obj.cliente.numero_documento
            )
        return format_html('<em>Público General</em>')
    cliente_display.short_description = 'Cliente'
    
    def total_display(self, obj):
        """Muestra el total de la venta"""
        total = format_currency(obj.total)
        return format_html(
            '<strong style="font-size: 14px;">{}</strong>',
            total
        )
    total_display.short_description = 'Total'
    
    def estado_display(self, obj):
        """Muestra el estado de la venta con colores"""
        estados = {
            'PENDIENTE': ('orange', '⏳', 'PENDIENTE'),
            'COMPLETADA': ('green', '✅', 'COMPLETADA'),
            'ANULADA': ('red', '❌', 'ANULADA'),
        }
        color, icono, texto = estados.get(obj.estado, ('black', '●', obj.estado))
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icono, texto
        )
    estado_display.short_description = 'Estado'
    
    def estado_pago_display(self, obj):
        """Muestra el estado del pago"""
        if obj.esta_pagada():
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ PAGADO</span>'
            )
        elif obj.monto_pagado > 0:
            saldo = format_currency(obj.saldo_pendiente())
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ PARCIAL</span><br><small>Saldo: {}</small>',
                saldo
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">❌ PENDIENTE</span>'
        )
    estado_pago_display.short_description = 'Estado Pago'
    
    def has_delete_permission(self, request, obj=None):
        """Solo permitir eliminar ventas pendientes"""
        if obj and obj.estado != 'PENDIENTE':
            return False
        return super().has_delete_permission(request, obj)


# ============================================================================
# ADMIN: Detalle Venta
# ============================================================================

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = [
        'venta_numero', 'producto', 'cantidad_display',
        'precio_display', 'subtotal_display',
        'descuento_porcentaje', 'total_display'
    ]
    list_filter = ['venta__fecha_venta', 'producto__categoria']
    search_fields = [
        'venta__numero_venta', 'producto__nombre',
        'producto__codigo_barras'
    ]
    ordering = ['-venta__fecha_venta', 'orden']
    
    readonly_fields = [
        'venta', 'producto', 'quintal', 'peso_vendido',
        'cantidad_unidades', 'precio_por_unidad_peso',
        'precio_unitario', 'subtotal', 'total', 'costo_unitario', 'costo_total'
    ]
    
    fieldsets = (
        ('Venta', {
            'fields': ('venta',)
        }),
        ('Producto', {
            'fields': ('producto', 'quintal')
        }),
        ('Cantidad y Precio', {
            'fields': (
                'peso_vendido', 'unidad_medida', 'precio_por_unidad_peso',
                'cantidad_unidades', 'precio_unitario'
            )
        }),
        ('Totales', {
            'fields': ('subtotal', 'descuento_porcentaje', 'descuento_monto', 'total')
        }),
        ('Costos', {
            'fields': ('costo_unitario', 'costo_total'),
            'classes': ('collapse',)
        }),
    )
    
    def venta_numero(self, obj):
        """Muestra el número de venta"""
        return obj.venta.numero_venta
    venta_numero.short_description = 'Venta'
    venta_numero.admin_order_field = 'venta__numero_venta'
    
    def cantidad_display(self, obj):
        """Muestra la cantidad vendida según el tipo de producto"""
        if obj.producto.es_quintal():
            return format_html(
                '<strong>{}</strong> {}',
                obj.peso_vendido,
                obj.unidad_medida.abreviatura if obj.unidad_medida else 'kg'
            )
        return format_html('<strong>{}</strong> unidades', obj.cantidad_unidades)
    cantidad_display.short_description = 'Cantidad'
    
    def precio_display(self, obj):
        """Muestra el precio según el tipo de producto"""
        if obj.producto.es_quintal():
            precio = format_currency(obj.precio_por_unidad_peso)
            unidad = obj.unidad_medida.abreviatura if obj.unidad_medida else 'kg'
            return format_html('{}/{}', precio, unidad)
        precio = format_currency(obj.precio_unitario)
        return format_html('{}/unidad', precio)
    precio_display.short_description = 'Precio'
    
    def subtotal_display(self, obj):
        """Muestra el subtotal"""
        subtotal = format_currency(obj.subtotal)
        return format_html('<span>{}</span>', subtotal)
    subtotal_display.short_description = 'Subtotal'
    
    def total_display(self, obj):
        """Muestra el total"""
        total = format_currency(obj.total)
        return format_html('<strong style="color: green;">{}</strong>', total)
    total_display.short_description = 'Total'
    
    def has_add_permission(self, request):
        """No permitir agregar detalles directamente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar detalles directamente"""
        return False


# ============================================================================
# ADMIN: Pago
# ============================================================================

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_pago', 'venta_numero', 'forma_pago_display',
        'monto_display', 'numero_referencia', 'banco', 'usuario'
    ]
    list_filter = ['forma_pago', 'fecha_pago', 'banco']
    search_fields = [
        'venta__numero_venta', 'numero_referencia', 
        'banco', 'venta__cliente__nombres'
    ]
    ordering = ['-fecha_pago']
    date_hierarchy = 'fecha_pago'
    
    fieldsets = (
        ('Venta', {
            'fields': ('venta',)
        }),
        ('Pago', {
            'fields': ('forma_pago', 'monto', 'fecha_pago')
        }),
        ('Detalles', {
            'fields': ('numero_referencia', 'banco')
        }),
        ('Usuario', {
            'fields': ('usuario',)
        }),
    )
    
    readonly_fields = [
        'venta', 'forma_pago', 'monto',
        'numero_referencia', 'banco', 'fecha_pago', 'usuario'
    ]
    
    def venta_numero(self, obj):
        """Muestra el número de venta"""
        return obj.venta.numero_venta
    venta_numero.short_description = 'Venta'
    venta_numero.admin_order_field = 'venta__numero_venta'
    
    def forma_pago_display(self, obj):
        """Muestra la forma de pago con ícono"""
        iconos = {
            'EFECTIVO': '💵',
            'TARJETA_DEBITO': '💳',
            'TARJETA_CREDITO': '💳',
            'TRANSFERENCIA': '🏦',
            'CHEQUE': '📝',
            'CREDITO': '📋',
        }
        icono = iconos.get(obj.forma_pago, '💰')
        return format_html('{} {}', icono, obj.get_forma_pago_display())
    forma_pago_display.short_description = 'Forma de Pago'
    forma_pago_display.admin_order_field = 'forma_pago'
    
    def monto_display(self, obj):
        """Muestra el monto del pago"""
        monto = format_currency(obj.monto)
        return format_html(
            '<strong style="color: green; font-size: 14px;">{}</strong>',
            monto
        )
    monto_display.short_description = 'Monto'
    monto_display.admin_order_field = 'monto'
    
    def has_add_permission(self, request):
        """No permitir agregar pagos directamente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar pagos directamente"""
        return False


# ============================================================================
# ADMIN: Devolución
# ============================================================================

@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = [
        'numero_devolucion', 'fecha_devolucion',
        'venta_numero', 'producto_devuelto', 'motivo_display',
        'monto_display', 'estado_display', 'usuario_solicita'
    ]
    list_filter = ['estado', 'motivo', 'fecha_devolucion']
    search_fields = [
        'numero_devolucion', 'venta_original__numero_venta',
        'descripcion', 'detalle_venta__producto__nombre'
    ]
    ordering = ['-fecha_devolucion']
    date_hierarchy = 'fecha_devolucion'
    
    fieldsets = (
        ('Información General', {
            'fields': ('numero_devolucion', 'venta_original', 'detalle_venta')
        }),
        ('Devolución', {
            'fields': ('cantidad_devuelta', 'monto_devolucion', 'motivo', 'descripcion')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Auditoría', {
            'fields': (
                'fecha_devolucion', 'usuario_solicita',
                'usuario_aprueba', 'fecha_procesado'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'numero_devolucion', 'fecha_devolucion',
        'usuario_solicita', 'usuario_aprueba', 'fecha_procesado', 'monto_devolucion'
    ]
    
    def venta_numero(self, obj):
        """Muestra el número de la venta original"""
        return obj.venta_original.numero_venta
    venta_numero.short_description = 'Venta'
    venta_numero.admin_order_field = 'venta_original__numero_venta'
    
    def producto_devuelto(self, obj):
        """Muestra el producto que se devolvió"""
        return obj.detalle_venta.producto.nombre
    producto_devuelto.short_description = 'Producto'
    
    def motivo_display(self, obj):
        """Muestra el motivo con ícono"""
        iconos = {
            'DEFECTUOSO': '🔧',
            'EQUIVOCACION': '❌',
            'NO_SATISFECHO': '😞',
            'VENCIDO': '📅',
            'OTRO': '❓',
        }
        icono = iconos.get(obj.motivo, '●')
        return format_html('{} {}', icono, obj.get_motivo_display())
    motivo_display.short_description = 'Motivo'
    motivo_display.admin_order_field = 'motivo'
    
    def monto_display(self, obj):
        """Muestra el monto de la devolución"""
        monto = format_currency(obj.monto_devolucion)
        return format_html(
            '<strong style="color: red;">{}</strong>',
            monto
        )
    monto_display.short_description = 'Monto'
    monto_display.admin_order_field = 'monto_devolucion'
    
    def estado_display(self, obj):
        """Muestra el estado de la devolución con colores"""
        estados = {
            'PENDIENTE': ('orange', '⏳', 'PENDIENTE'),
            'APROBADA': ('green', '✅', 'APROBADA'),
            'RECHAZADA': ('red', '❌', 'RECHAZADA'),
        }
        color, icono, texto = estados.get(obj.estado, ('black', '●', obj.estado))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icono, texto
        )
    estado_display.short_description = 'Estado'
    estado_display.admin_order_field = 'estado'
    
    def has_delete_permission(self, request, obj=None):
        """Solo permitir eliminar devoluciones pendientes"""
        if obj and obj.estado != 'PENDIENTE':
            return False
        return super().has_delete_permission(request, obj)


# ============================================================================
# ACCIONES PERSONALIZADAS
# ============================================================================

@admin.action(description='Marcar como activo')
def marcar_activo(modeladmin, request, queryset):
    """Acción para marcar clientes como activos"""
    count = queryset.update(activo=True)
    modeladmin.message_user(
        request,
        f'{count} cliente(s) marcado(s) como activo(s).'
    )


@admin.action(description='Marcar como inactivo')
def marcar_inactivo(modeladmin, request, queryset):
    """Acción para marcar clientes como inactivos"""
    count = queryset.update(activo=False)
    modeladmin.message_user(
        request,
        f'{count} cliente(s) marcado(s) como inactivo(s).'
    )


# Agregar acciones al ClienteAdmin
ClienteAdmin.actions = [marcar_activo, marcar_inactivo]


# ============================================================================
# CONFIGURACIÓN DEL ADMIN SITE
# ============================================================================

# Personalizar el título del admin
admin.site.site_header = 'CommerceBox - Administración de Ventas'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Panel de Administración de Ventas'