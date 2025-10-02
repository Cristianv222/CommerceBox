# apps/sales_management/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from decimal import Decimal

from .models import Cliente, Venta, DetalleVenta, Pago, Devolucion


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
        if obj.nombre_comercial:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.nombre_comercial,
                obj.nombre_completo()
            )
        return obj.nombre_completo()
    nombre_completo_display.short_description = 'Cliente'
    
    def credito_display(self, obj):
        if obj.limite_credito > 0:
            porcentaje = (obj.credito_disponible / obj.limite_credito) * 100
            if porcentaje > 50:
                color = 'green'
            elif porcentaje > 20:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">${:,.2f} / ${:,.2f}</span>',
                color, float(obj.credito_disponible), float(obj.limite_credito)
            )
        return '-'
    credito_display.short_description = 'Crédito Disponible'
    
    def total_compras_display(self, obj):
        total = obj.total_compras
        # Asegurar que el valor es un número
        if isinstance(total, (Decimal, float, int)):
            return format_html(
                '<strong>${:,.2f}</strong>',
                float(total)
            )
        # Si es string o SafeString, intentar convertir
        try:
            total_num = float(str(total).replace('$', '').replace(',', ''))
            return format_html(
                '<strong>${:,.2f}</strong>',
                total_num
            )
        except (ValueError, AttributeError):
            return total
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
        if obj.cliente:
            return format_html(
                '{}<br><small>{}</small>',
                obj.cliente.nombre_completo(),
                obj.cliente.numero_documento
            )
        return format_html('<em>Público General</em>')
    cliente_display.short_description = 'Cliente'
    
    def total_display(self, obj):
        return format_html(
            '<strong style="font-size: 14px;">${:,.2f}</strong>',
            float(obj.total)
        )
    total_display.short_description = 'Total'
    
    def estado_display(self, obj):
        estados = {
            'PENDIENTE': ('orange', 'PEND'),
            'COMPLETADA': ('green', 'COMP'),
            'ANULADA': ('red', 'ANUL'),
        }
        color, texto = estados.get(obj.estado, ('black', obj.estado))
        return format_html(
            '<span style="color: {}; font-weight: bold;">[{}]</span>',
            color, texto
        )
    estado_display.short_description = 'Estado'
    
    def estado_pago_display(self, obj):
        if obj.esta_pagada():
            return format_html('<span style="color: green;">PAGADO</span>')
        elif obj.monto_pagado > 0:
            saldo = obj.saldo_pendiente()
            return format_html(
                '<span style="color: orange;">PARCIAL<br>${:,.2f}</span>',
                float(saldo)
            )
        return format_html('<span style="color: red;">PENDIENTE</span>')
    estado_pago_display.short_description = 'Pago'
    
    def has_delete_permission(self, request, obj=None):
        # Solo permitir eliminar ventas pendientes
        if obj and obj.estado != 'PENDIENTE':
            return False
        return super().has_delete_permission(request, obj)


# ============================================================================
# ADMIN: Detalle Venta
# ============================================================================

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = [
        'venta', 'producto', 'cantidad_display',
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
        'precio_unitario', 'subtotal', 'total'
    ]
    
    def cantidad_display(self, obj):
        if obj.producto.es_quintal():
            return format_html(
                '{} {}',
                obj.peso_vendido,
                obj.unidad_medida.abreviatura
            )
        return f"{obj.cantidad_unidades} unidades"
    cantidad_display.short_description = 'Cantidad'
    
    def precio_display(self, obj):
        if obj.producto.es_quintal():
            return f"${obj.precio_por_unidad_peso}/{obj.unidad_medida.abreviatura}"
        return f"${obj.precio_unitario}/unidad"
    precio_display.short_description = 'Precio'
    
    def subtotal_display(self, obj):
        return format_html('${:,.2f}', float(obj.subtotal))
    subtotal_display.short_description = 'Subtotal'
    
    def total_display(self, obj):
        return format_html('<strong>${:,.2f}</strong>', float(obj.total))
    total_display.short_description = 'Total'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# ADMIN: Pago
# ============================================================================

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_pago', 'venta', 'forma_pago',
        'monto_display', 'numero_referencia', 'usuario'
    ]
    list_filter = ['forma_pago', 'fecha_pago']
    search_fields = [
        'venta__numero_venta', 'numero_referencia', 'banco'
    ]
    ordering = ['-fecha_pago']
    date_hierarchy = 'fecha_pago'
    
    readonly_fields = [
        'venta', 'forma_pago', 'monto',
        'numero_referencia', 'banco', 'fecha_pago', 'usuario'
    ]
    
    def monto_display(self, obj):
        return format_html('<strong>${:,.2f}</strong>', float(obj.monto))
    monto_display.short_description = 'Monto'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# ADMIN: Devolución
# ============================================================================

@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = [
        'numero_devolucion', 'fecha_devolucion',
        'venta_original', 'motivo', 'monto_display',
        'estado_display', 'usuario_solicita'
    ]
    list_filter = ['estado', 'motivo', 'fecha_devolucion']
    search_fields = [
        'numero_devolucion', 'venta_original__numero_venta',
        'descripcion'
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
        'usuario_solicita', 'usuario_aprueba', 'fecha_procesado'
    ]
    
    def monto_display(self, obj):
        return format_html('<strong>${:,.2f}</strong>', float(obj.monto_devolucion))
    monto_display.short_description = 'Monto'
    
    def estado_display(self, obj):
        estados = {
            'PENDIENTE': ('orange', 'PEND'),
            'APROBADA': ('green', 'APROB'),
            'RECHAZADA': ('red', 'RECH'),
        }
        color, texto = estados.get(obj.estado, ('black', obj.estado))
        return format_html(
            '<span style="color: {}; font-weight: bold;">[{}]</span>',
            color, texto
        )
    estado_display.short_description = 'Estado'