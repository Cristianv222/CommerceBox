# apps/inventory_management/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, F, Q
from decimal import Decimal

from .models import (
    Categoria, Proveedor, Marca, UnidadMedida, Producto,
    Quintal, MovimientoQuintal, ProductoNormal,
    MovimientoInventario, Compra, DetalleCompra, ConversionUnidad
)


# ============================================================================
# INLINES (Modelos relacionados)
# ============================================================================

class MovimientoQuintalInline(admin.TabularInline):
    """Inline para ver movimientos de un quintal"""
    model = MovimientoQuintal
    extra = 0
    readonly_fields = [
        'tipo_movimiento', 'peso_movimiento', 'peso_antes',
        'peso_despues', 'usuario', 'fecha_movimiento', 'unidad_medida'
    ]
    fields = [
        'tipo_movimiento', 'peso_movimiento', 'peso_antes',
        'peso_despues', 'unidad_medida', 'usuario', 'fecha_movimiento'
    ]
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


class MovimientoInventarioInline(admin.TabularInline):
    """Inline para ver movimientos de producto normal"""
    model = MovimientoInventario
    extra = 0
    readonly_fields = [
        'tipo_movimiento', 'cantidad', 'stock_antes',
        'stock_despues', 'usuario', 'fecha_movimiento'
    ]
    fields = [
        'tipo_movimiento', 'cantidad', 'stock_antes',
        'stock_despues', 'usuario', 'fecha_movimiento'
    ]
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


class DetalleCompraInline(admin.TabularInline):
    """Inline para detalles de compra"""
    model = DetalleCompra
    extra = 1
    fields = [
        'producto', 'peso_comprado', 'unidad_medida',
        'cantidad_unidades', 'costo_unitario', 'subtotal'
    ]
    readonly_fields = ['subtotal']
    autocomplete_fields = ['producto', 'unidad_medida']


# ============================================================================
# ADMIN: Categoría
# ============================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'margen_ganancia_sugerido',
        'descuento_maximo_permitido', 'activa',
        'cantidad_productos', 'orden'
    ]
    list_filter = ['activa']
    search_fields = ['nombre', 'descripcion']
    ordering = ['orden', 'nombre']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'orden')
        }),
        ('Configuración Comercial', {
            'fields': ('margen_ganancia_sugerido', 'descuento_maximo_permitido')
        }),
        ('Control', {
            'fields': ('activa',)
        }),
    )
    
    def cantidad_productos(self, obj):
        count = obj.productos.filter(activo=True).count()
        return format_html(
            '<span style="font-weight: bold;">{} productos</span>',
            count
        )
    cantidad_productos.short_description = 'Productos'


# ============================================================================
# ADMIN: Marca
# ============================================================================

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'pais_origen', 'destacada_display',
        'activa', 'cantidad_productos', 'orden'
    ]
    list_filter = ['activa', 'destacada', 'pais_origen']
    search_fields = ['nombre', 'descripcion', 'fabricante', 'pais_origen']
    ordering = ['orden', 'nombre']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'logo')
        }),
        ('Información Adicional', {
            'fields': ('pais_origen', 'fabricante', 'sitio_web')
        }),
        ('Control', {
            'fields': ('activa', 'destacada', 'orden')
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    def destacada_display(self, obj):
        if obj.destacada:
            return format_html(
                '<span style="color: gold; font-weight: bold;">⭐ DESTACADA</span>'
            )
        return format_html(
            '<span style="color: gray;">-</span>'
        )
    destacada_display.short_description = 'Destacada'
    
    def cantidad_productos(self, obj):
        count = obj.total_productos()
        con_stock = obj.productos_con_stock().count()
        return format_html(
            '<span style="font-weight: bold;">{} productos</span><br>'
            '<small style="color: green;">({} con stock)</small>',
            count, con_stock
        )
    cantidad_productos.short_description = 'Productos'
    
    actions = ['marcar_destacada', 'desmarcar_destacada', 'activar_marcas', 'desactivar_marcas']
    
    def marcar_destacada(self, request, queryset):
        updated = queryset.update(destacada=True)
        self.message_user(request, f"{updated} marcas marcadas como destacadas.")
    marcar_destacada.short_description = "⭐ Marcar como destacadas"
    
    def desmarcar_destacada(self, request, queryset):
        updated = queryset.update(destacada=False)
        self.message_user(request, f"{updated} marcas desmarcadas como destacadas.")
    desmarcar_destacada.short_description = "Desmarcar destacadas"
    
    def activar_marcas(self, request, queryset):
        updated = queryset.update(activa=True)
        self.message_user(request, f"{updated} marcas activadas.")
    activar_marcas.short_description = "Activar marcas seleccionadas"
    
    def desactivar_marcas(self, request, queryset):
        updated = queryset.update(activa=False)
        self.message_user(request, f"{updated} marcas desactivadas.")
    desactivar_marcas.short_description = "Desactivar marcas seleccionadas"


# ============================================================================
# ADMIN: Proveedor
# ============================================================================

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_comercial', 'ruc_nit', 'telefono',
        'email', 'activo', 'total_compras'
    ]
    list_filter = ['activo']
    search_fields = ['nombre_comercial', 'razon_social', 'ruc_nit']
    ordering = ['nombre_comercial']
    
    fieldsets = (
        ('Información Comercial', {
            'fields': ('nombre_comercial', 'razon_social', 'ruc_nit')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email', 'direccion')
        }),
        ('Términos Comerciales', {
            'fields': ('dias_credito', 'limite_credito')
        }),
        ('Control', {
            'fields': ('activo',)
        }),
    )
    
    def total_compras(self, obj):
        total = obj.compras.filter(estado='RECIBIDA').count()
        return f"{total} compras"
    total_compras.short_description = 'Compras'


# ============================================================================
# ADMIN: Unidad de Medida
# ============================================================================

@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'abreviatura', 'factor_conversion_kg',
        'es_sistema_metrico', 'activa', 'orden_display'
    ]
    list_filter = ['es_sistema_metrico', 'activa']
    search_fields = ['nombre', 'abreviatura']
    ordering = ['orden_display', 'nombre']
    
    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'abreviatura')
        }),
        ('Conversión', {
            'fields': ('factor_conversion_kg', 'es_sistema_metrico'),
            'description': 'Factor de conversión a kilogramos (kg = 1.0)'
        }),
        ('Configuración', {
            'fields': ('orden_display', 'activa')
        }),
    )


# ============================================================================
# ADMIN: Producto (Maestro)
# ============================================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'tipo_icon', 'nombre', 'codigo_barras',
        'marca', 'categoria', 'tipo_inventario',
        'precio_display', 'stock_display', 'activo'
    ]
    list_filter = [
        'tipo_inventario', 'categoria', 'marca',
        'activo', 'fecha_creacion'
    ]
    search_fields = [
        'nombre', 'codigo_barras', 'descripcion',
        'marca__nombre'
    ]
    ordering = ['-fecha_creacion']
    autocomplete_fields = ['categoria', 'marca', 'proveedor', 'unidad_medida_base']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo_barras', 'nombre', 'descripcion', 'imagen')
        }),
        ('Clasificación', {
            'fields': ('categoria', 'marca', 'proveedor', 'tipo_inventario')
        }),
        ('Configuración para QUINTALES', {
            'fields': (
                'unidad_medida_base', 'precio_por_unidad_peso',
                'peso_base_quintal'
            ),
            'classes': ('collapse',),
            'description': 'Solo para productos tipo QUINTAL'
        }),
        ('Configuración para PRODUCTOS NORMALES', {
            'fields': ('precio_unitario',),
            'classes': ('collapse',),
            'description': 'Solo para productos tipo NORMAL'
        }),
        ('Impuestos', {
            'fields': ('iva',)
        }),
        ('Control', {
            'fields': ('activo', 'usuario_registro')
        }),
    )
    
    readonly_fields = ['usuario_registro']
    
    def tipo_icon(self, obj):
        if obj.tipo_inventario == 'QUINTAL':
            return format_html('<span style="color: green;">🌾 Quintal</span>')
        return format_html('<span style="color: blue;">📦 Normal</span>')
    tipo_icon.short_description = 'Tipo'
    
    def precio_display(self, obj):
        if obj.tipo_inventario == 'QUINTAL':
            if obj.unidad_medida_base:
                return f"${obj.precio_por_unidad_peso}/{obj.unidad_medida_base.abreviatura}"
            return f"${obj.precio_por_unidad_peso}"
        return f"${obj.precio_unitario}/unidad"
    precio_display.short_description = 'Precio'
    
    def stock_display(self, obj):
        try:
            stock = obj.get_stock_total()
            if obj.tipo_inventario == 'QUINTAL':
                quintales_disponibles = obj.quintales.filter(
                    estado='DISPONIBLE',
                    peso_actual__gt=0
                ).count()
                return format_html(
                    '<span style="font-weight: bold;">{}</span><br>'
                    '<small>({} quintales)</small>',
                    stock, quintales_disponibles
                )
            else:
                try:
                    inventario = obj.inventario_normal
                    estado = inventario.estado_stock()
                    if estado == 'AGOTADO':
                        color = 'red'
                    elif estado == 'CRITICO':
                        color = 'orange'
                    elif estado == 'BAJO':
                        color = 'gold'
                    else:
                        color = 'green'
                    return format_html(
                        '<span style="color: {}; font-weight: bold;">{}</span>',
                        color, stock
                    )
                except:
                    return stock
        except:
            return '-'
    stock_display.short_description = 'Stock'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_registro = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activar_productos', 'desactivar_productos']
    
    def activar_productos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} productos activados.")
    activar_productos.short_description = "Activar productos seleccionados"
    
    def desactivar_productos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} productos desactivados.")
    desactivar_productos.short_description = "Desactivar productos seleccionados"


# ============================================================================
# ADMIN: Quintal
# ============================================================================

@admin.register(Quintal)
class QuintalAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_unico', 'producto_display', 'estado_display',
        'peso_actual_display', 'porcentaje_display',
        'proveedor', 'fecha_recepcion'
    ]
    list_filter = [
        'estado', 'producto__categoria', 'producto__marca',
        'proveedor', 'fecha_recepcion'
    ]
    search_fields = [
        'codigo_unico', 'producto__nombre',
        'producto__marca__nombre',
        'lote_proveedor', 'numero_factura_compra'
    ]
    ordering = ['-fecha_recepcion']
    date_hierarchy = 'fecha_recepcion'
    autocomplete_fields = ['producto', 'proveedor', 'unidad_medida']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo_unico', 'producto', 'proveedor')
        }),
        ('Peso y Estado', {
            'fields': (
                'peso_inicial', 'peso_actual', 'unidad_medida', 'estado'
            )
        }),
        ('Costos', {
            'fields': ('costo_total', 'costo_por_unidad')
        }),
        ('Trazabilidad', {
            'fields': (
                'fecha_recepcion', 'fecha_vencimiento',
                'lote_proveedor', 'numero_factura_compra', 'origen'
            )
        }),
        ('Auditoría', {
            'fields': ('usuario_registro',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['costo_por_unidad', 'usuario_registro']
    
    inlines = [MovimientoQuintalInline]
    
    def producto_display(self, obj):
        if obj.producto.marca:
            return format_html(
                '{}<br><small style="color: gray;">{}</small>',
                obj.producto.nombre,
                obj.producto.marca.nombre
            )
        return obj.producto.nombre
    producto_display.short_description = 'Producto'
    
    def estado_display(self, obj):
        if obj.estado == 'DISPONIBLE':
            icon = '🟢'
            color = 'green'
        elif obj.estado == 'AGOTADO':
            icon = '⚫'
            color = 'gray'
        else:
            icon = '🔴'
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'
    
    def peso_actual_display(self, obj):
        peso_actual_fmt = f"{obj.peso_actual:.2f}"
        peso_inicial_fmt = f"{obj.peso_inicial:.2f}"
        
        return format_html(
            '<strong>{}</strong> / {} {}',
            peso_actual_fmt, peso_inicial_fmt,
            obj.unidad_medida.abreviatura
        )
    peso_actual_display.short_description = 'Peso Actual/Inicial'
    
    def porcentaje_display(self, obj):
        porcentaje = obj.porcentaje_restante()
        if porcentaje > 50:
            color = 'green'
        elif porcentaje > 20:
            color = 'orange'
        else:
            color = 'red'
        
        porcentaje_width = f"{porcentaje:.0f}"
        porcentaje_text = f"{porcentaje:.1f}"
        
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 5px;">'
            '<div style="width: {}%; background: {}; color: white; '
            'text-align: center; border-radius: 5px; padding: 2px;">{}%</div>'
            '</div>',
            porcentaje_width, color, porcentaje_text
        )
    porcentaje_display.short_description = '% Restante'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_registro = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# ADMIN: Movimiento Quintal
# ============================================================================

@admin.register(MovimientoQuintal)
class MovimientoQuintalAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_movimiento', 'quintal', 'tipo_movimiento',
        'peso_movimiento_display', 'peso_antes', 'peso_despues', 'usuario'
    ]
    list_filter = [
        'tipo_movimiento', 'fecha_movimiento', 'usuario'
    ]
    search_fields = [
        'quintal__codigo_unico', 'quintal__producto__nombre',
        'quintal__producto__marca__nombre',
        'observaciones'
    ]
    ordering = ['-fecha_movimiento']
    date_hierarchy = 'fecha_movimiento'
    autocomplete_fields = ['quintal', 'unidad_medida']
    
    readonly_fields = [
        'quintal', 'tipo_movimiento', 'peso_movimiento',
        'peso_antes', 'peso_despues', 'unidad_medida',
        'venta', 'usuario', 'fecha_movimiento'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def peso_movimiento_display(self, obj):
        if obj.peso_movimiento >= 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">+{} {}</span>',
                obj.peso_movimiento, obj.unidad_medida.abreviatura
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} {}</span>',
                obj.peso_movimiento, obj.unidad_medida.abreviatura
            )
    peso_movimiento_display.short_description = 'Movimiento'


# ============================================================================
# ADMIN: Producto Normal
# ============================================================================

@admin.register(ProductoNormal)
class ProductoNormalAdmin(admin.ModelAdmin):
    list_display = [
        'producto_display', 'stock_display', 'valor_inventario_display',
        'estado_stock_display', 'ubicacion_almacen'
    ]
    list_filter = [
        'producto__categoria', 'producto__marca',
        'fecha_ultima_entrada'
    ]
    search_fields = [
        'producto__nombre', 'producto__codigo_barras',
        'producto__marca__nombre',
        'lote', 'ubicacion_almacen'
    ]
    ordering = ['producto__nombre']
    autocomplete_fields = ['producto']
    
    fieldsets = (
        ('Producto', {
            'fields': ('producto',)
        }),
        ('Stock', {
            'fields': (
                'stock_actual', 'stock_minimo', 'stock_maximo'
            )
        }),
        ('Costos', {
            'fields': ('costo_unitario',)
        }),
        ('Información Adicional', {
            'fields': (
                'lote', 'fecha_vencimiento', 'ubicacion_almacen'
            )
        }),
        ('Auditoría', {
            'fields': (
                'fecha_ultima_entrada', 'fecha_ultima_salida'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_ultima_entrada', 'fecha_ultima_salida']
    
    inlines = [MovimientoInventarioInline]
    
    def producto_display(self, obj):
        if obj.producto.marca:
            return format_html(
                '{}<br><small style="color: gray;">{}</small>',
                obj.producto.nombre,
                obj.producto.marca.nombre
            )
        return obj.producto.nombre
    producto_display.short_description = 'Producto'
    
    def stock_display(self, obj):
        estado = obj.estado_stock()
        if estado == 'AGOTADO':
            color = 'red'
            icon = '⚫'
        elif estado == 'CRITICO':
            color = 'red'
            icon = '🔴'
        elif estado == 'BAJO':
            color = 'orange'
            icon = '🟡'
        else:
            color = 'green'
            icon = '🟢'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} unidades</span>'
            '<br><small>Min: {} | Max: {}</small>',
            color, icon, obj.stock_actual,
            obj.stock_minimo, obj.stock_maximo or 'N/A'
        )
    stock_display.short_description = 'Stock'
    
    def estado_stock_display(self, obj):
        estado = obj.estado_stock()
        estados = {
            'AGOTADO': ('red', 'AGOTADO'),
            'CRITICO': ('red', 'CRITICO'),
            'BAJO': ('orange', 'BAJO'),
            'NORMAL': ('green', 'NORMAL')
        }
        color, texto = estados.get(estado, ('black', estado))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, texto
        )
    estado_stock_display.short_description = 'Estado'
    
    def valor_inventario_display(self, obj):
        valor = obj.valor_inventario()
        
        if isinstance(valor, (Decimal, float, int)):
            valor_num = float(valor)
        else:
            try:
                valor_num = float(str(valor).replace('$', '').replace(',', ''))
            except (ValueError, AttributeError):
                return valor
        
        valor_formateado = f"${valor_num:,.2f}"
        
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            valor_formateado
        )
    valor_inventario_display.short_description = 'Valor'


# ============================================================================
# ADMIN: Movimiento Inventario
# ============================================================================

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_movimiento', 'producto_normal', 'tipo_movimiento',
        'cantidad_display', 'stock_antes', 'stock_despues', 'usuario'
    ]
    list_filter = [
        'tipo_movimiento', 'fecha_movimiento', 'usuario'
    ]
    search_fields = [
        'producto_normal__producto__nombre',
        'producto_normal__producto__marca__nombre',
        'observaciones'
    ]
    ordering = ['-fecha_movimiento']
    date_hierarchy = 'fecha_movimiento'
    autocomplete_fields = ['producto_normal']
    
    readonly_fields = [
        'producto_normal', 'tipo_movimiento', 'cantidad',
        'stock_antes', 'stock_despues', 'costo_unitario',
        'costo_total', 'venta', 'compra', 'usuario',
        'fecha_movimiento'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def cantidad_display(self, obj):
        if obj.cantidad >= 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">+{} unidades</span>',
                obj.cantidad
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} unidades</span>',
                obj.cantidad
            )
    cantidad_display.short_description = 'Movimiento'


# ============================================================================
# ADMIN: Compra
# ============================================================================

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = [
        'numero_compra', 'proveedor', 'fecha_compra',
        'estado_display', 'total_display', 'usuario_registro'
    ]
    list_filter = ['estado', 'fecha_compra', 'proveedor']
    search_fields = ['numero_compra', 'numero_factura', 'proveedor__nombre_comercial']
    ordering = ['-fecha_compra']
    date_hierarchy = 'fecha_compra'
    autocomplete_fields = ['proveedor']
    
    fieldsets = (
        ('Información de Compra', {
            'fields': ('numero_compra', 'proveedor', 'numero_factura')
        }),
        ('Fechas', {
            'fields': ('fecha_compra', 'fecha_recepcion')
        }),
        ('Totales', {
            'fields': ('subtotal', 'descuento', 'impuestos', 'total')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('usuario_registro', 'usuario_recepcion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['usuario_registro', 'usuario_recepcion']
    
    inlines = [DetalleCompraInline]
    
    def estado_display(self, obj):
        estados = {
            'PENDIENTE': ('orange', 'PENDIENTE'),
            'RECIBIDA': ('green', 'RECIBIDA'),
            'PARCIAL': ('gold', 'PARCIAL'),
            'CANCELADA': ('red', 'CANCELADA')
        }
        color, texto = estados.get(obj.estado, ('black', obj.estado))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'
    
    def total_display(self, obj):
        total_formateado = f"${float(obj.total):,.2f}"
        
        return format_html(
            '<span style="font-weight: bold; font-size: 14px;">{}</span>',
            total_formateado
        )
    total_display.short_description = 'Total'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_registro = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# ADMIN: Conversión Unidad
# ============================================================================

@admin.register(ConversionUnidad)
class ConversionUnidadAdmin(admin.ModelAdmin):
    list_display = [
        'descripcion_display', 'unidad_origen',
        'unidad_destino', 'factor_conversion'
    ]
    list_filter = ['unidad_origen', 'unidad_destino']
    search_fields = ['descripcion']
    autocomplete_fields = ['unidad_origen', 'unidad_destino']
    
    def descripcion_display(self, obj):
        return obj.descripcion or str(obj)
    descripcion_display.short_description = 'Conversión'