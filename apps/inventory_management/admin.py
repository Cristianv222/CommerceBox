# apps/inventory_management/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, F, Q, Count
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
    
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    def cantidad_productos(self, obj):
        count = obj.productos.filter(activo=True).count()
        return format_html(
            '<span style="font-weight: bold;">{} productos</span>',
            count
        )
    cantidad_productos.short_description = 'Productos'
    
    actions = ['activar_categorias', 'desactivar_categorias']
    
    def activar_categorias(self, request, queryset):
        updated = queryset.update(activa=True)
        self.message_user(request, f"{updated} categorías activadas.")
    activar_categorias.short_description = "Activar categorías seleccionadas"
    
    def desactivar_categorias(self, request, queryset):
        updated = queryset.update(activa=False)
        self.message_user(request, f"{updated} categorías desactivadas.")
    desactivar_categorias.short_description = "Desactivar categorías seleccionadas"


# ============================================================================
# ADMIN: Marca
# ============================================================================

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'pais_origen', 'fabricante',
        'destacada_display', 'activa', 'cantidad_productos',
        'productos_stock', 'valor_inventario', 'orden'
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
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
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
        return format_html(
            '<span style="font-weight: bold; color: #0066cc;">{}</span>',
            count
        )
    cantidad_productos.short_description = 'Total Productos'
    
    def productos_stock(self, obj):
        con_stock = obj.productos_con_stock().count()
        return format_html(
            '<span style="color: green; font-weight: bold;">🟢 {}</span>',
            con_stock
        )
    productos_stock.short_description = 'Con Stock'
    
    def valor_inventario(self, obj):
        valor = obj.valor_inventario_marca()
        return format_html(
            '<span style="font-weight: bold; color: #009900;">${:,.2f}</span>',
            float(valor)
        )
    valor_inventario.short_description = 'Valor Inventario'
    
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
        'email', 'dias_credito', 'limite_credito',
        'activo', 'total_compras'
    ]
    list_filter = ['activo', 'dias_credito']
    search_fields = ['nombre_comercial', 'razon_social', 'ruc_nit', 'email']
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
        ('Auditoría', {
            'fields': ('fecha_registro', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_registro', 'fecha_actualizacion']
    
    def total_compras(self, obj):
        total = obj.compras.filter(estado='RECIBIDA').count()
        pendientes = obj.compras.filter(estado='PENDIENTE').count()
        
        html = f'<span style="font-weight: bold; color: green;">{total} recibidas</span>'
        if pendientes > 0:
            html += f'<br><small style="color: orange;">{pendientes} pendientes</small>'
        
        return format_html(html)
    total_compras.short_description = 'Compras'
    
    actions = ['activar_proveedores', 'desactivar_proveedores']
    
    def activar_proveedores(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} proveedores activados.")
    activar_proveedores.short_description = "Activar proveedores seleccionados"
    
    def desactivar_proveedores(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} proveedores desactivados.")
    desactivar_proveedores.short_description = "Desactivar proveedores seleccionados"


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
        ('Control', {
            'fields': ('activa', 'orden_display')
        }),
    )
    
    readonly_fields = ['fecha_creacion']
    
    actions = ['activar_unidades', 'desactivar_unidades']
    
    def activar_unidades(self, request, queryset):
        updated = queryset.update(activa=True)
        self.message_user(request, f"{updated} unidades de medida activadas.")
    activar_unidades.short_description = "Activar unidades seleccionadas"
    
    def desactivar_unidades(self, request, queryset):
        updated = queryset.update(activa=False)
        self.message_user(request, f"{updated} unidades de medida desactivadas.")
    desactivar_unidades.short_description = "Desactivar unidades seleccionadas"


# ============================================================================
# ADMIN: Producto
# ============================================================================
# apps/inventory_management/admin.py - CORREGIR ProductoAdmin

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_barras', 'nombre_display', 'tipo_inventario',
        'precio_display', 'marca', 'categoria',  # ✅ Cambiado de 'precio_venta' a 'precio_display'
        'stock_display', 'stock_total_display', 'activo'
    ]
    list_filter = [
        'tipo_inventario', 'activo', 'categoria',
        'marca', 'aplica_impuestos'
    ]
    search_fields = [
        'codigo_barras', 'nombre', 'descripcion',
        'marca__nombre', 'categoria__nombre'
    ]
    ordering = ['nombre']
    autocomplete_fields = ['categoria', 'marca', 'unidad_medida_base']
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'codigo_barras', 'nombre', 'descripcion',
                'tipo_inventario', 'marca', 'categoria'
            )
        }),
        ('Unidades de Medida', {
            'fields': ('unidad_medida_base',),
            'description': 'Unidad de medida base para el producto'
        }),
        ('Precios e Impuestos', {
            'fields': (
                'precio_venta', 'precio_por_unidad_peso',
                'aplica_impuestos'
            )
        }),
        ('✅ Stock Calculado', {
            'fields': (
                'cantidad_quintales', 'peso_base_quintal',
                'stock_total_calculado'
            ),
            'description': 'Para quintales: cantidad × peso base = stock total'
        }),
        ('Control', {
            'fields': ('activo', 'imagen')
        }),
    )
    
    # ✅ CORREGIDO: Solo campos que realmente existen en el modelo
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    # ============================================================================
    # ✅ MÉTODOS PERSONALIZADOS PARA LIST_DISPLAY
    # ============================================================================
    
    def nombre_display(self, obj):
        if obj.marca:
            return format_html(
                '<strong>{}</strong><br><small style="color: gray;">{}</small>',
                obj.nombre,
                obj.marca.nombre
            )
        return format_html('<strong>{}</strong>', obj.nombre)
    nombre_display.short_description = 'Producto'
    
    def precio_display(self, obj):
        """Mostrar precio según tipo"""
        if obj.es_quintal():
            if obj.precio_por_unidad_peso:
                unidad = obj.unidad_medida_base.abreviatura if obj.unidad_medida_base else 'kg'
                return format_html(
                    '<span style="color: #059669; font-weight: bold;">${}/{}</span>',
                    obj.precio_por_unidad_peso,
                    unidad
                )
        else:
            if obj.precio_venta:
                return format_html(
                    '<span style="color: #059669; font-weight: bold;">${}</span>',
                    obj.precio_venta
                )
        return format_html('<span style="color: gray;">-</span>')
    precio_display.short_description = 'Precio'
    
    def stock_display(self, obj):
        if obj.es_quintal():
            # Para quintales - mostrar info resumida
            return format_html(
                '<span style="color: #3b82f6; font-weight: bold;">🌾 {} quintales</span>',
                obj.cantidad_quintales or 0
            )
        else:
            # Para productos normales
            try:
                inventario = obj.inventario_normal
                estado = inventario.estado_stock()
                
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
                    '<span style="color: {}; font-weight: bold;">{} {} unidades</span>',
                    color, icon, inventario.stock_actual
                )
            except ProductoNormal.DoesNotExist:
                return format_html(
                    '<span style="color: gray;">Sin inventario</span>'
                )
    stock_display.short_description = 'Estado Stock'
    
    def stock_total_display(self, obj):
        if obj.es_quintal():
            return format_html(
                '<span style="color: #3b82f6; font-weight: bold;">{} {}</span>'
                '<br><small>{} quintales × {} {}</small>',
                obj.stock_total_calculado,
                obj.unidad_medida_base.abreviatura if obj.unidad_medida_base else 'lb',
                obj.cantidad_quintales,
                obj.peso_base_quintal or 100,
                obj.unidad_medida_base.abreviatura if obj.unidad_medida_base else 'lb'
            )
        else:
            return format_html(
                '<span style="color: #059669; font-weight: bold;">{} unidades</span>',
                obj.stock_total_calculado or 0
            )
    stock_total_display.short_description = 'Stock Total'
    
    # ============================================================================
    # ✅ ACCIONES DEL ADMIN
    # ============================================================================
    
    actions = [
        'activar_productos', 'desactivar_productos', 
        'aplicar_impuestos', 'quitar_impuestos',
        'calcular_stock_automaticamente'
    ]
    
    def activar_productos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} productos activados.")
    activar_productos.short_description = "Activar productos seleccionados"
    
    def desactivar_productos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} productos desactivados.")
    desactivar_productos.short_description = "Desactivar productos seleccionados"
    
    def aplicar_impuestos(self, request, queryset):
        updated = queryset.update(aplica_impuestos=True)
        self.message_user(request, f"{updated} productos ahora aplican impuestos.")
    aplicar_impuestos.short_description = "Aplicar impuestos a productos seleccionados"
    
    def quitar_impuestos(self, request, queryset):
        updated = queryset.update(aplica_impuestos=False)
        self.message_user(request, f"{updated} productos ahora NO aplican impuestos.")
    quitar_impuestos.short_description = "Quitar impuestos de productos seleccionados"
    
    def calcular_stock_automaticamente(self, request, queryset):
        for producto in queryset:
            producto.actualizar_stock_calculado()
        self.message_user(request, f"Stock calculado para {queryset.count()} productos.")
    calcular_stock_automaticamente.short_description = "📊 Calcular stock automáticamente"
    
# ============================================================================
# ADMIN: Quintal
# ============================================================================

@admin.register(Quintal)
class QuintalAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_quintal', 'producto_display', 'proveedor',
        'peso_display', 'estado_display', 'fecha_ingreso',
        'dias_almacenado', 'vencimiento_display'
    ]
    list_filter = [
        'estado', 'fecha_ingreso', 'proveedor',
        'producto__categoria', 'producto__marca'
    ]
    search_fields = [
        'codigo_quintal', 'producto__nombre',
        'producto__marca__nombre', 'proveedor__nombre_comercial'
    ]
    ordering = ['-fecha_ingreso']
    date_hierarchy = 'fecha_ingreso'
    autocomplete_fields = ['producto', 'proveedor', 'unidad_medida']
    
    fieldsets = (
        ('Producto', {
            'fields': ('producto', 'codigo_quintal')
        }),
        ('Proveedor y Compra', {
            'fields': ('proveedor', 'compra', 'fecha_ingreso')
        }),
        ('Peso', {
            'fields': (
                'peso_inicial', 'peso_actual', 'unidad_medida'
            )
        }),
        ('Costos', {
            'fields': ('costo_total', 'costo_por_unidad')
        }),
        ('Vencimiento', {
            'fields': ('fecha_vencimiento',)
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Auditoría', {
            'fields': ('usuario_registro',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['codigo_quintal', 'costo_por_unidad', 'usuario_registro']
    
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
    
    def peso_display(self, obj):
        porcentaje = (obj.peso_actual / obj.peso_inicial * 100) if obj.peso_inicial > 0 else 0
        
        if porcentaje <= 10:
            color = 'red'
            icon = '🔴'
        elif porcentaje <= 30:
            color = 'orange'
            icon = '🟡'
        else:
            color = 'green'
            icon = '🟢'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} / {} {}</span>'
            '<br><small>{}%</small>',
            color, icon,
            obj.peso_actual, obj.peso_inicial,
            obj.unidad_medida.abreviatura,
            round(porcentaje, 1)
        )
    peso_display.short_description = 'Peso Actual / Inicial'
    
    def estado_display(self, obj):
        estados = {
            'DISPONIBLE': ('green', 'DISPONIBLE'),
            'RESERVADO': ('orange', 'RESERVADO'),
            'AGOTADO': ('red', 'AGOTADO')
        }
        color, texto = estados.get(obj.estado, ('black', obj.estado))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, texto
        )
    estado_display.short_description = 'Estado'
    
    def dias_almacenado(self, obj):
        dias = obj.dias_almacenamiento()
        if dias > 90:
            color = 'red'
        elif dias > 60:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {};">{} días</span>',
            color, dias
        )
    dias_almacenado.short_description = 'Días Almacén'
    
    def vencimiento_display(self, obj):
        if not obj.fecha_vencimiento:
            return format_html('<span style="color: gray;">N/A</span>')
        
        dias = obj.dias_para_vencer()
        
        if dias is None:
            return format_html('<span style="color: gray;">Sin fecha</span>')
        elif dias < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ VENCIDO</span>'
            )
        elif dias <= 7:
            return format_html(
                '<span style="color: red; font-weight: bold;">🔴 {} días</span>',
                dias
            )
        elif dias <= 30:
            return format_html(
                '<span style="color: orange; font-weight: bold;">🟡 {} días</span>',
                dias
            )
        else:
            return format_html(
                '<span style="color: green;">{} días</span>',
                dias
            )
    vencimiento_display.short_description = 'Vencimiento'
    
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
        'fecha_movimiento', 'quintal_display', 'tipo_movimiento',
        'peso_movimiento_display', 'peso_antes', 'peso_despues',
        'unidad_medida', 'usuario'
    ]
    list_filter = [
        'tipo_movimiento', 'fecha_movimiento', 'usuario',
        'unidad_medida'
    ]
    search_fields = [
        'quintal__codigo_quintal',
        'quintal__producto__nombre',
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
    
    def quintal_display(self, obj):
        return format_html(
            '{}<br><small style="color: gray;">{}</small>',
            obj.quintal.producto.nombre,
            obj.quintal.codigo_quintal
        )
    quintal_display.short_description = 'Quintal'
    
    def peso_movimiento_display(self, obj):
        if obj.tipo_movimiento in ['ENTRADA', 'ENTRADA_DEVOLUCION', 'AJUSTE_ENTRADA']:
            return format_html(
                '<span style="color: green; font-weight: bold;">+{} {}</span>',
                obj.peso_movimiento,
                obj.unidad_medida.abreviatura
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">-{} {}</span>',
                obj.peso_movimiento,
                obj.unidad_medida.abreviatura
            )
    peso_movimiento_display.short_description = 'Movimiento'


# ============================================================================
# ADMIN: Producto Normal
# ============================================================================

@admin.register(ProductoNormal)
class ProductoNormalAdmin(admin.ModelAdmin):
    list_display = [
        'producto_display', 'stock_display', 'estado_stock_display',
        'costo_unitario', 'valor_inventario_display',
        'lote', 'vencimiento_display'
    ]
    list_filter = [
        'fecha_vencimiento', 'fecha_ultima_entrada',
        'producto__categoria', 'producto__marca'
    ]
    search_fields = [
        'producto__nombre', 'producto__codigo_barras',
        'producto__marca__nombre', 'lote'
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
    
    def vencimiento_display(self, obj):
        if not obj.fecha_vencimiento:
            return format_html('<span style="color: gray;">N/A</span>')
        
        dias = obj.dias_para_vencer()
        
        if dias is None:
            return format_html('<span style="color: gray;">Sin fecha</span>')
        elif dias < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ VENCIDO</span>'
            )
        elif dias <= 7:
            return format_html(
                '<span style="color: red; font-weight: bold;">🔴 {} días</span>',
                dias
            )
        elif dias <= 30:
            return format_html(
                '<span style="color: orange; font-weight: bold;">🟡 {} días</span>',
                dias
            )
        else:
            return format_html(
                '<span style="color: green;">{} días</span>',
                dias
            )
    vencimiento_display.short_description = 'Vencimiento'


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
    
    fieldsets = (
        ('Unidades', {
            'fields': ('unidad_origen', 'unidad_destino')
        }),
        ('Conversión', {
            'fields': ('factor_conversion', 'descripcion')
        }),
    )
    
    def descripcion_display(self, obj):
        return obj.descripcion or str(obj)
    descripcion_display.short_description = 'Conversión'
    
    def save_model(self, request, obj, form, change):
        """Actualizar la descripción automáticamente si está vacía"""
        if not obj.descripcion:
            obj.descripcion = f"1 {obj.unidad_origen.abreviatura} = {obj.factor_conversion} {obj.unidad_destino.abreviatura}"
        super().save_model(request, obj, form, change)


# ============================================================================
# ADMIN: Detalle Compra
# ============================================================================

@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = [
        'compra', 'producto', 'peso_comprado',
        'unidad_medida', 'cantidad_unidades',
        'costo_unitario', 'subtotal'
    ]
    list_filter = ['compra__fecha_compra', 'producto__categoria', 'producto__marca']
    search_fields = [
        'compra__numero_compra',
        'producto__nombre',
        'producto__marca__nombre'
    ]
    ordering = ['-compra__fecha_compra']
    autocomplete_fields = ['compra', 'producto', 'unidad_medida']
    
    readonly_fields = ['subtotal']
    
    def has_add_permission(self, request):
        """No permitir crear detalles desde aquí"""
        return False