# apps/financial_management/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from decimal import Decimal

from .models import (
    Caja, MovimientoCaja, ArqueoCaja,
    CajaChica, MovimientoCajaChica,
    CuentaPorCobrar, PagoCuentaPorCobrar,
    CuentaPorPagar, PagoCuentaPorPagar
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_currency(amount):
    """Helper para formatear montos como moneda"""
    if amount is None:
        return '$0.00'
    return f'${float(amount):,.2f}'


# ============================================================================
# ADMIN: CAJA
# ============================================================================

@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'tipo', 'estado_badge', 
        'monto_actual', 'fecha_apertura', 'usuario_apertura'
    ]
    list_filter = ['estado', 'tipo', 'activa']
    search_fields = ['codigo', 'nombre']
    readonly_fields = [
        'fecha_apertura', 'fecha_cierre', 
        'usuario_apertura', 'usuario_cierre',
        'fecha_creacion', 'fecha_actualizacion'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'tipo')
        }),
        ('Estado Actual', {
            'fields': (
                'estado', 'monto_apertura', 'monto_actual',
                'fecha_apertura', 'fecha_cierre'
            )
        }),
        ('Usuarios', {
            'fields': ('usuario_apertura', 'usuario_cierre')
        }),
        ('Configuración', {
            'fields': ('requiere_autorizacion_cierre', 'activa')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def estado_badge(self, obj):
        if obj.estado == 'ABIERTA':
            color = 'green'
            icon = '🟢'
        else:
            color = 'red'
            icon = '🔴'
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_movimiento', 'caja', 'tipo_movimiento',
        'monto_formatted', 'saldo_nuevo', 'usuario'
    ]
    list_filter = ['tipo_movimiento', 'caja', 'fecha_movimiento']
    search_fields = ['caja__nombre', 'observaciones']
    readonly_fields = [
        'fecha_movimiento', 'saldo_anterior', 'saldo_nuevo'
    ]
    date_hierarchy = 'fecha_movimiento'
    
    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('caja', 'tipo_movimiento', 'monto')
        }),
        ('Referencias', {
            'fields': ('venta',)
        }),
        ('Auditoría', {
            'fields': ('usuario', 'fecha_movimiento', 'observaciones')
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        """Mostrar saldos solo al editar (no al crear)"""
        fieldsets = super().get_fieldsets(request, obj)
        if obj:  # Si está editando
            fieldsets = list(fieldsets)
            fieldsets.insert(1, ('Saldos (Calculados Automáticamente)', {
                'fields': ('saldo_anterior', 'saldo_nuevo')
            }))
        return fieldsets
    
    def monto_formatted(self, obj):
        return f"${obj.monto:,.2f}"
    monto_formatted.short_description = 'Monto'


@admin.register(ArqueoCaja)
class ArqueoCajaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_arqueo', 'caja', 'fecha_cierre',
        'monto_esperado', 'monto_contado', 'diferencia_formatted',
        'estado_badge'
    ]
    list_filter = ['estado', 'caja', 'fecha_cierre']
    search_fields = ['numero_arqueo', 'caja__nombre']
    readonly_fields = [
        'numero_arqueo', 'diferencia', 'estado',
        'fecha_creacion'
    ]
    date_hierarchy = 'fecha_cierre'
    
    fieldsets = (
        ('Información General', {
            'fields': ('numero_arqueo', 'caja', 'fecha_apertura', 'fecha_cierre')
        }),
        ('Montos Calculados (Sistema)', {
            'fields': (
                'monto_apertura', 'total_ventas',
                'total_ingresos', 'total_retiros', 'monto_esperado'
            )
        }),
        ('Conteo Físico', {
            'fields': (
                'billetes_100', 'billetes_50', 'billetes_20',
                'billetes_10', 'billetes_5', 'billetes_1', 'monedas',
                'monto_contado'
            )
        }),
        ('Resultado', {
            'fields': ('diferencia', 'estado')
        }),
        ('Observaciones', {
            'fields': ('observaciones', 'observaciones_diferencia')
        }),
        ('Usuarios', {
            'fields': ('usuario_apertura', 'usuario_cierre')
        }),
    )
    
    def diferencia_formatted(self, obj):
        if obj.diferencia == 0:
            color = 'green'
            icon = '✅'
        elif obj.diferencia > 0:
            color = 'blue'
            icon = '➕'
        else:
            color = 'red'
            icon = '➖'
        monto_formateado = f'{abs(obj.diferencia):,.2f}'
        return format_html(
            '<span style="color: {};">{} ${}</span>',
            color, icon, monto_formateado
        )
    diferencia_formatted.short_description = 'Diferencia'
    
    def estado_badge(self, obj):
        colors = {
            'CUADRADO': 'green',
            'SOBRANTE': 'blue',
            'FALTANTE': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.estado, 'black'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'


# ============================================================================
# ADMIN: CAJA CHICA
# ============================================================================

@admin.register(CajaChica)
class CajaChicaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'monto_actual_formatted',
        'monto_fondo', 'necesita_reposicion_badge',
        'responsable', 'estado'
    ]
    list_filter = ['estado', 'responsable']
    search_fields = ['codigo', 'nombre']
    readonly_fields = [
        'fecha_creacion', 'fecha_actualizacion',
        'fecha_ultima_reposicion'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'responsable')
        }),
        ('Fondos', {
            'fields': (
                'monto_fondo', 'monto_actual',
                'umbral_reposicion', 'fecha_ultima_reposicion'
            )
        }),
        ('Límites', {
            'fields': ('limite_gasto_individual',)
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def monto_actual_formatted(self, obj):
        porcentaje = (obj.monto_actual / obj.monto_fondo * 100) if obj.monto_fondo > 0 else 0
        if porcentaje < 30:
            color = 'red'
        elif porcentaje < 50:
            color = 'orange'
        else:
            color = 'green'
        monto_formateado = f'{obj.monto_actual:,.2f}'
        porcentaje_formateado = f'{porcentaje:.0f}'
        return format_html(
            '<span style="color: {};">${} ({}%)</span>',
            color, monto_formateado, porcentaje_formateado
        )
    monto_actual_formatted.short_description = 'Saldo Actual'
    
    def necesita_reposicion_badge(self, obj):
        if obj.necesita_reposicion():
            monto_formateado = f'{obj.monto_a_reponer():,.2f}'
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Sí - ${}</span>',
                monto_formateado
            )
        return format_html('<span style="color: green;">✅ No</span>')
    necesita_reposicion_badge.short_description = 'Necesita Reposición'


@admin.register(MovimientoCajaChica)
class MovimientoCajaChicaAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_movimiento', 'caja_chica', 'tipo_movimiento',
        'categoria_gasto', 'monto_formatted', 'saldo_nuevo', 'usuario'
    ]
    list_filter = [
        'tipo_movimiento', 'categoria_gasto',
        'caja_chica', 'fecha_movimiento'
    ]
    search_fields = ['caja_chica__nombre', 'descripcion', 'numero_comprobante']
    readonly_fields = ['fecha_movimiento', 'saldo_anterior', 'saldo_nuevo']
    date_hierarchy = 'fecha_movimiento'
    
    fieldsets = (
        ('Información del Movimiento', {
            'fields': (
                'caja_chica', 'tipo_movimiento',
                'categoria_gasto', 'monto'
            )
        }),
        ('Detalles', {
            'fields': (
                'descripcion', 'numero_comprobante',
                'comprobante_adjunto'
            )
        }),
        ('Auditoría', {
            'fields': ('usuario', 'fecha_movimiento')
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        """Mostrar saldos solo al editar (no al crear)"""
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            fieldsets = list(fieldsets)
            fieldsets.insert(1, ('Saldos (Calculados Automáticamente)', {
                'fields': ('saldo_anterior', 'saldo_nuevo')
            }))
        return fieldsets
    
    def monto_formatted(self, obj):
        monto_formateado = f'{obj.monto:,.2f}'
        if obj.tipo_movimiento == 'GASTO':
            return format_html(
                '<span style="color: red;">-${}</span>',
                monto_formateado
            )
        return format_html(
            '<span style="color: green;">+${}</span>',
            monto_formateado
        )
    monto_formatted.short_description = 'Monto'


# ============================================================================
# ADMIN: CUENTAS POR COBRAR
# ============================================================================

class PagoCuentaPorCobrarInline(admin.TabularInline):
    """Inline para mostrar pagos en la cuenta por cobrar"""
    model = PagoCuentaPorCobrar
    extra = 0
    readonly_fields = ('numero_pago', 'fecha_pago', 'usuario')
    fields = ('numero_pago', 'monto', 'metodo_pago', 'numero_comprobante', 'banco', 'fecha_pago', 'observaciones', 'usuario')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = (
        'numero_cuenta', 
        'get_cliente_nombre', 
        'get_venta_numero',
        'monto_total_display', 
        'monto_pagado_display',
        'saldo_pendiente_display',
        'fecha_emision',
        'fecha_vencimiento',
        'get_dias_vencimiento',
        'get_estado_badge'
    )
    
    list_filter = (
        'estado',
        'fecha_emision',
        'fecha_vencimiento',
        ('cliente', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'numero_cuenta',
        'cliente__nombres',
        'cliente__apellidos',
        'cliente__numero_documento',
        'cliente__nombre_comercial',
        'venta__numero_venta',
        'descripcion'
    )
    
    readonly_fields = (
        'numero_cuenta',
        'monto_pagado',
        'saldo_pendiente',
        'estado',
        'dias_vencidos',
        'fecha_pago_completo',
        'fecha_registro',
        'fecha_actualizacion'
    )
    
    fieldsets = (
        ('Información General', {
            'fields': (
                'numero_cuenta',
                'cliente',
                'venta',
                'descripcion'
            )
        }),
        ('Montos', {
            'fields': (
                'monto_total',
                'monto_pagado',
                'saldo_pendiente'
            )
        }),
        ('Fechas', {
            'fields': (
                'fecha_emision',
                'fecha_vencimiento',
                'fecha_pago_completo'
            )
        }),
        ('Estado', {
            'fields': (
                'estado',
                'dias_vencidos',
                'observaciones'
            )
        }),
        ('Auditoría', {
            'fields': (
                'usuario_registro',
                'fecha_registro',
                'fecha_actualizacion'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [PagoCuentaPorCobrarInline]
    date_hierarchy = 'fecha_emision'
    actions = ['marcar_como_cancelada']
    
    def get_cliente_nombre(self, obj):
        """Muestra el nombre del cliente"""
        if obj.cliente.nombre_comercial:
            return format_html(
                '<strong>{}</strong><br><small>{} {}</small>',
                obj.cliente.nombre_comercial,
                obj.cliente.nombres,
                obj.cliente.apellidos
            )
        return format_html(
            '{} {}',
            obj.cliente.nombres,
            obj.cliente.apellidos
        )
    get_cliente_nombre.short_description = 'Cliente'
    
    def get_venta_numero(self, obj):
        """Muestra el número de venta con link"""
        if obj.venta:
            url = reverse('admin:sales_management_venta_change', args=[obj.venta.pk])
            return format_html('<a href="{}" target="_blank">🔗 {}</a>', url, obj.venta.numero_venta)
        return '-'
    get_venta_numero.short_description = 'Venta'
    
    def monto_total_display(self, obj):
        return format_html(
            '<strong style="font-size: 13px;">{}</strong>',
            format_currency(obj.monto_total)
        )
    monto_total_display.short_description = 'Total'
    monto_total_display.admin_order_field = 'monto_total'
    
    def monto_pagado_display(self, obj):
        return format_html(
            '<span style="color: green;">{}</span>',
            format_currency(obj.monto_pagado)
        )
    monto_pagado_display.short_description = 'Pagado'
    monto_pagado_display.admin_order_field = 'monto_pagado'
    
    def saldo_pendiente_display(self, obj):
        color = 'red' if obj.saldo_pendiente > 0 else 'green'
        return format_html(
            '<strong style="color: {}; font-size: 13px;">{}</strong>',
            color,
            format_currency(obj.saldo_pendiente)
        )
    saldo_pendiente_display.short_description = 'Saldo'
    saldo_pendiente_display.admin_order_field = 'saldo_pendiente'
    
    def get_dias_vencimiento(self, obj):
        """Muestra días para vencer o vencidos"""
        dias = obj.dias_para_vencer()
        if dias > 0:
            if dias <= 7:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⚠️ {} días</span>',
                    dias
                )
            return format_html(
                '<span style="color: green;">⏰ {} días</span>',
                dias
            )
        elif dias == 0:
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ Vence hoy</span>')
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">🔴 {} días vencido</span>',
                abs(dias)
            )
    get_dias_vencimiento.short_description = 'Vencimiento'
    
    def get_estado_badge(self, obj):
        """Muestra el estado con badge de color"""
        colors = {
            'PENDIENTE': '#FFA500',
            'PARCIAL': '#FF8C00',
            'PAGADA': '#28a745',
            'VENCIDA': '#dc3545',
            'CANCELADA': '#6c757d'
        }
        icons = {
            'PENDIENTE': '🟡',
            'PARCIAL': '🟠',
            'PAGADA': '🟢',
            'VENCIDA': '🔴',
            'CANCELADA': '⚫'
        }
        color = colors.get(obj.estado, '#6c757d')
        icon = icons.get(obj.estado, '●')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_estado_display()
        )
    get_estado_badge.short_description = 'Estado'
    get_estado_badge.admin_order_field = 'estado'
    
    def marcar_como_cancelada(self, request, queryset):
        """Acción para marcar cuentas como canceladas"""
        count = queryset.filter(monto_pagado=0, estado__in=['PENDIENTE', 'VENCIDA']).update(estado='CANCELADA')
        self.message_user(request, f'{count} cuenta(s) marcada(s) como cancelada(s)')
    marcar_como_cancelada.short_description = 'Marcar como cancelada'


@admin.register(PagoCuentaPorCobrar)
class PagoCuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = (
        'numero_pago',
        'get_cuenta_numero',
        'get_cliente_nombre',
        'monto_display',
        'get_metodo_pago_badge',
        'numero_comprobante',
        'fecha_pago',
        'usuario'
    )
    
    list_filter = (
        'metodo_pago',
        'fecha_pago',
        ('cuenta__cliente', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'numero_pago',
        'cuenta__numero_cuenta',
        'cuenta__cliente__nombres',
        'cuenta__cliente__apellidos',
        'cuenta__cliente__nombre_comercial',
        'numero_comprobante',
        'observaciones'
    )
    
    readonly_fields = (
        'numero_pago',
        'fecha_pago'
    )
    
    fieldsets = (
        ('Información del Pago', {
            'fields': (
                'numero_pago',
                'cuenta',
                'monto',
                'metodo_pago'
            )
        }),
        ('Detalles Adicionales', {
            'fields': (
                'numero_comprobante',
                'banco',
                'numero_cuenta_banco',
                'observaciones'
            )
        }),
        ('Auditoría', {
            'fields': (
                'usuario',
                'fecha_pago'
            )
        })
    )
    
    date_hierarchy = 'fecha_pago'
    
    def get_cuenta_numero(self, obj):
        url = reverse('admin:financial_management_cuentaporcobrar_change', args=[obj.cuenta.pk])
        return format_html('<a href="{}" target="_blank">🔗 {}</a>', url, obj.cuenta.numero_cuenta)
    get_cuenta_numero.short_description = 'Cuenta'
    
    def get_cliente_nombre(self, obj):
        if obj.cuenta.cliente.nombre_comercial:
            return obj.cuenta.cliente.nombre_comercial
        return f"{obj.cuenta.cliente.nombres} {obj.cuenta.cliente.apellidos}"
    get_cliente_nombre.short_description = 'Cliente'
    
    def monto_display(self, obj):
        return format_html(
            '<strong style="color: green; font-size: 13px;">{}</strong>',
            format_currency(obj.monto)
        )
    monto_display.short_description = 'Monto'
    monto_display.admin_order_field = 'monto'
    
    def get_metodo_pago_badge(self, obj):
        iconos = {
            'EFECTIVO': '💵',
            'TRANSFERENCIA': '🏦',
            'TARJETA_DEBITO': '💳',
            'TARJETA_CREDITO': '💳',
            'CHEQUE': '📝',
            'DEPOSITO': '🏦',
            'OTRO': '📦'
        }
        icono = iconos.get(obj.metodo_pago, '💰')
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 4px 10px; border-radius: 3px;">{} {}</span>',
            icono,
            obj.get_metodo_pago_display()
        )
    get_metodo_pago_badge.short_description = 'Método Pago'
    get_metodo_pago_badge.admin_order_field = 'metodo_pago'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# ADMIN: CUENTAS POR PAGAR
# ============================================================================

class PagoCuentaPorPagarInline(admin.TabularInline):
    """Inline para mostrar pagos en la cuenta por pagar"""
    model = PagoCuentaPorPagar
    extra = 0
    readonly_fields = ('numero_pago', 'fecha_pago', 'usuario')
    fields = ('numero_pago', 'monto', 'metodo_pago', 'numero_comprobante', 'banco', 'fecha_pago', 'observaciones', 'usuario')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CuentaPorPagar)
class CuentaPorPagarAdmin(admin.ModelAdmin):
    list_display = (
        'numero_cuenta',
        'get_proveedor_nombre',
        'numero_factura_proveedor',
        'get_tipo_compra_badge',
        'monto_total_display',
        'monto_pagado_display',
        'saldo_pendiente_display',
        'fecha_emision',
        'fecha_vencimiento',
        'get_dias_vencimiento',
        'get_estado_badge'
    )
    
    list_filter = (
        'estado',
        'tipo_compra',
        'fecha_emision',
        'fecha_vencimiento',
        ('proveedor', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'numero_cuenta',
        'numero_factura_proveedor',
        'proveedor__nombre_comercial',
        'proveedor__ruc_nit',
        'descripcion'
    )
    
    readonly_fields = (
        'numero_cuenta',
        'monto_pagado',
        'saldo_pendiente',
        'estado',
        'dias_vencidos',
        'fecha_pago_completo',
        'fecha_registro',
        'fecha_actualizacion'
    )
    
    fieldsets = (
        ('Información General', {
            'fields': (
                'numero_cuenta',
                'proveedor',
                'tipo_compra',
                'numero_factura_proveedor',
                'descripcion'
            )
        }),
        ('Montos', {
            'fields': (
                'monto_total',
                'monto_pagado',
                'saldo_pendiente'
            )
        }),
        ('Fechas', {
            'fields': (
                'fecha_emision',
                'fecha_factura',
                'fecha_vencimiento',
                'fecha_pago_completo'
            )
        }),
        ('Estado', {
            'fields': (
                'estado',
                'dias_vencidos',
                'observaciones'
            )
        }),
        ('Auditoría', {
            'fields': (
                'usuario_registro',
                'fecha_registro',
                'fecha_actualizacion'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [PagoCuentaPorPagarInline]
    date_hierarchy = 'fecha_emision'
    actions = ['marcar_como_cancelada']
    
    def get_proveedor_nombre(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.proveedor.nombre_comercial,
            obj.proveedor.ruc_nit
        )
    get_proveedor_nombre.short_description = 'Proveedor'
    
    def get_tipo_compra_badge(self, obj):
        colors = {
            'QUINTAL': '#6f42c1',
            'NORMAL': '#007bff',
            'MIXTA': '#17a2b8',
            'SERVICIO': '#ffc107',
            'OTRO': '#6c757d'
        }
        icons = {
            'QUINTAL': '⚖️',
            'NORMAL': '📦',
            'MIXTA': '🛒',
            'SERVICIO': '🔧',
            'OTRO': '📋'
        }
        color = colors.get(obj.tipo_compra, '#6c757d')
        icon = icons.get(obj.tipo_compra, '●')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 3px;">{} {}</span>',
            color,
            icon,
            obj.get_tipo_compra_display()
        )
    get_tipo_compra_badge.short_description = 'Tipo'
    get_tipo_compra_badge.admin_order_field = 'tipo_compra'
    
    def monto_total_display(self, obj):
        return format_html(
            '<strong style="font-size: 13px;">{}</strong>',
            format_currency(obj.monto_total)
        )
    monto_total_display.short_description = 'Total'
    monto_total_display.admin_order_field = 'monto_total'
    
    def monto_pagado_display(self, obj):
        return format_html(
            '<span style="color: green;">{}</span>',
            format_currency(obj.monto_pagado)
        )
    monto_pagado_display.short_description = 'Pagado'
    monto_pagado_display.admin_order_field = 'monto_pagado'
    
    def saldo_pendiente_display(self, obj):
        color = 'red' if obj.saldo_pendiente > 0 else 'green'
        return format_html(
            '<strong style="color: {}; font-size: 13px;">{}</strong>',
            color,
            format_currency(obj.saldo_pendiente)
        )
    saldo_pendiente_display.short_description = 'Saldo'
    saldo_pendiente_display.admin_order_field = 'saldo_pendiente'
    
    def get_dias_vencimiento(self, obj):
        dias = obj.dias_para_vencer()
        if dias > 0:
            if dias <= 7:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⚠️ {} días</span>',
                    dias
                )
            return format_html(
                '<span style="color: green;">⏰ {} días</span>',
                dias
            )
        elif dias == 0:
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ Vence hoy</span>')
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">🔴 {} días vencido</span>',
                abs(dias)
            )
    get_dias_vencimiento.short_description = 'Vencimiento'
    
    def get_estado_badge(self, obj):
        colors = {
            'PENDIENTE': '#FFA500',
            'PARCIAL': '#FF8C00',
            'PAGADA': '#28a745',
            'VENCIDA': '#dc3545',
            'CANCELADA': '#6c757d'
        }
        icons = {
            'PENDIENTE': '🟡',
            'PARCIAL': '🟠',
            'PAGADA': '🟢',
            'VENCIDA': '🔴',
            'CANCELADA': '⚫'
        }
        color = colors.get(obj.estado, '#6c757d')
        icon = icons.get(obj.estado, '●')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_estado_display()
        )
    get_estado_badge.short_description = 'Estado'
    get_estado_badge.admin_order_field = 'estado'
    
    def marcar_como_cancelada(self, request, queryset):
        count = queryset.filter(monto_pagado=0, estado__in=['PENDIENTE', 'VENCIDA']).update(estado='CANCELADA')
        self.message_user(request, f'{count} cuenta(s) marcada(s) como cancelada(s)')
    marcar_como_cancelada.short_description = 'Marcar como cancelada'


@admin.register(PagoCuentaPorPagar)
class PagoCuentaPorPagarAdmin(admin.ModelAdmin):
    list_display = (
        'numero_pago',
        'get_cuenta_numero',
        'get_proveedor_nombre',
        'monto_display',
        'get_metodo_pago_badge',
        'numero_comprobante',
        'fecha_pago',
        'usuario'
    )
    
    list_filter = (
        'metodo_pago',
        'fecha_pago',
        ('cuenta__proveedor', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'numero_pago',
        'cuenta__numero_cuenta',
        'cuenta__proveedor__nombre_comercial',
        'numero_comprobante',
        'observaciones'
    )
    
    readonly_fields = (
        'numero_pago',
        'fecha_pago'
    )
    
    fieldsets = (
        ('Información del Pago', {
            'fields': (
                'numero_pago',
                'cuenta',
                'monto',
                'metodo_pago'
            )
        }),
        ('Detalles Adicionales', {
            'fields': (
                'numero_comprobante',
                'banco',
                'numero_cuenta_banco',
                'observaciones'
            )
        }),
        ('Auditoría', {
            'fields': (
                'usuario',
                'fecha_pago'
            )
        })
    )
    
    date_hierarchy = 'fecha_pago'
    
    def get_cuenta_numero(self, obj):
        url = reverse('admin:financial_management_cuentaporpagar_change', args=[obj.cuenta.pk])
        return format_html('<a href="{}" target="_blank">🔗 {}</a>', url, obj.cuenta.numero_cuenta)
    get_cuenta_numero.short_description = 'Cuenta'
    
    def get_proveedor_nombre(self, obj):
        return obj.cuenta.proveedor.nombre_comercial
    get_proveedor_nombre.short_description = 'Proveedor'
    
    def monto_display(self, obj):
        return format_html(
            '<strong style="color: green; font-size: 13px;">{}</strong>',
            format_currency(obj.monto)
        )
    monto_display.short_description = 'Monto'
    monto_display.admin_order_field = 'monto'
    
    def get_metodo_pago_badge(self, obj):
        iconos = {
            'EFECTIVO': '💵',
            'TRANSFERENCIA': '🏦',
            'CHEQUE': '📝',
            'DEPOSITO': '🏦',
            'TARJETA_CREDITO': '💳',
            'OTRO': '📦'
        }
        icono = iconos.get(obj.metodo_pago, '💰')
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 4px 10px; border-radius: 3px;">{} {}</span>',
            icono,
            obj.get_metodo_pago_display()
        )
    get_metodo_pago_badge.short_description = 'Método Pago'
    get_metodo_pago_badge.admin_order_field = 'metodo_pago'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# CONFIGURACIÓN DEL ADMIN SITE
# ============================================================================

admin.site.site_header = 'CommerceBox - Gestión Financiera'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Panel de Administración Financiera'