# apps/inventory_management/forms.py

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    Categoria, Marca, Proveedor, Producto, Quintal,
    ProductoNormal, UnidadMedida, Compra, DetalleCompra
)
from .utils.barcode_generator import BarcodeGenerator


# ============================================================================
# FORMULARIOS PARA CATEGORÍAS
# ============================================================================

class CategoriaForm(forms.ModelForm):
    """Formulario para crear/editar categorías"""
    
    class Meta:
        model = Categoria
        fields = [
            'nombre', 'descripcion', 'margen_ganancia_sugerido',
            'descuento_maximo_permitido', 'orden', 'activa'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción opcional'
            }),
            'margen_ganancia_sugerido': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'descuento_maximo_permitido': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_descuento_maximo_permitido(self):
        descuento = self.cleaned_data.get('descuento_maximo_permitido')
        if descuento and descuento > 100:
            raise ValidationError("El descuento no puede ser mayor a 100%")
        return descuento


# ============================================================================
# FORMULARIOS PARA MARCAS
# ============================================================================

class MarcaForm(forms.ModelForm):
    """Formulario para crear/editar marcas"""
    
    class Meta:
        model = Marca
        fields = [
            'nombre', 'descripcion', 'logo',
            'pais_origen', 'fabricante', 'sitio_web',
            'activa', 'destacada', 'orden'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la marca',
                'required': True
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la marca (opcional)'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'pais_origen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Ecuador, Colombia, México',
                'list': 'paises-list'
            }),
            'fabricante': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del fabricante (opcional)'
            }),
            'sitio_web': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.ejemplo.com'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'destacada': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '0'
            })
        }
        labels = {
            'nombre': 'Nombre de la Marca',
            'descripcion': 'Descripción',
            'logo': 'Logo de la Marca',
            'pais_origen': 'País de Origen',
            'fabricante': 'Fabricante',
            'sitio_web': 'Sitio Web',
            'activa': 'Activa',
            'destacada': 'Marca Destacada',
            'orden': 'Orden de Visualización'
        }
        help_texts = {
            'destacada': 'Las marcas destacadas aparecen en el dashboard y en destacados',
            'orden': 'Menor número = mayor prioridad en listados',
            'sitio_web': 'URL completa (debe comenzar con http:// o https://)'
        }
    
    def clean_nombre(self):
        """Validar que el nombre no esté duplicado (case insensitive)"""
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            nombre = nombre.strip()
            
            # Verificar duplicados
            qs = Marca.objects.filter(nombre__iexact=nombre)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(
                    f'Ya existe una marca con el nombre "{nombre}"'
                )
        
        return nombre
    
    def clean_sitio_web(self):
        """Validar formato de URL"""
        sitio_web = self.cleaned_data.get('sitio_web')
        if sitio_web:
            sitio_web = sitio_web.strip()
            if not sitio_web.startswith(('http://', 'https://')):
                raise ValidationError(
                    'La URL debe comenzar con http:// o https://'
                )
        return sitio_web
    
    def clean_orden(self):
        """Asegurar que el orden sea positivo"""
        orden = self.cleaned_data.get('orden')
        if orden is None:
            orden = 0
        elif orden < 0:
            raise ValidationError('El orden no puede ser negativo')
        return orden


# ============================================================================
# FORMULARIOS PARA PROVEEDORES
# ============================================================================

class ProveedorForm(forms.ModelForm):
    """Formulario para crear/editar proveedores"""
    
    class Meta:
        model = Proveedor
        fields = [
            'nombre_comercial', 'razon_social', 'ruc_nit',
            'telefono', 'email', 'direccion',
            'dias_credito', 'limite_credito', 'activo'
        ]
        widgets = {
            'nombre_comercial': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre comercial'
            }),
            'razon_social': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón social'
            }),
            'ruc_nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+593 99 999 9999'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'proveedor@example.com'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'dias_credito': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'limite_credito': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


# ============================================================================
# FORMULARIOS PARA PRODUCTOS
# ============================================================================

class ProductoForm(forms.ModelForm):
    """
    Formulario para crear/editar productos (maestro)
    ✅ CORREGIDO: Campos actualizados según nuevo modelo
    """
    
    generar_codigo_automatico = forms.BooleanField(
        required=False,
        initial=True,
        label='Generar código automáticamente',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Producto
        fields = [
            'codigo_barras', 'nombre', 'descripcion', 'categoria',
            'marca', 'tipo_inventario', 'imagen', 'activo',
            # ✅ NUEVO: Campo para indicar si graba IVA
            'aplica_impuestos',
            # Para quintales
            'unidad_medida_base', 'precio_por_unidad_peso', 'peso_base_quintal',
            # Para normales
            'precio_venta'  # ✅ CORREGIDO: antes era precio_unitario
        ]
        widgets = {
            'codigo_barras': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CBX-PRD-00001 o escanea código'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del producto (opcional)'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'marca': forms.Select(attrs={
                'class': 'form-select',
                'required': False
            }),
            # ✅ Campo proveedor eliminado - ya no existe en Producto
            'tipo_inventario': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_tipo_inventario'
            }),
            'unidad_medida_base': forms.Select(attrs={
                'class': 'form-select'
            }),
            'precio_por_unidad_peso': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0',
                'placeholder': '0.0000'
            }),
            'peso_base_quintal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': '100.000'
            }),
            # ✅ CORREGIDO: precio_venta en lugar de precio_unitario
            'precio_venta': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            # ✅ NUEVO: Widget para aplica_impuestos
            'aplica_impuestos': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_aplica_impuestos'
            })
        }
        labels = {
            'marca': 'Marca (opcional)',
            'aplica_impuestos': 'Graba IVA',  # ✅ NUEVO
            'precio_venta': 'Precio de Venta (sin IVA)',  # ✅ NUEVO
            'precio_por_unidad_peso': 'Precio por Unidad de Peso (sin IVA)'  # ✅ NUEVO
        }
        help_texts = {
            'aplica_impuestos': 'Marcar si este producto graba IVA al venderse',
            'precio_venta': 'Precio SIN IVA - el IVA se calculará automáticamente en la venta',
            'precio_por_unidad_peso': 'Precio SIN IVA por kg/lb - el IVA se calculará en la venta'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo marcas activas
        self.fields['marca'].queryset = Marca.objects.filter(activa=True).order_by('nombre')
        
        # Hacer que marca sea opcional
        self.fields['marca'].required = False
        
        # Si es edición, deshabilitar generar automático
        if self.instance and self.instance.pk:
            self.fields['generar_codigo_automatico'].initial = False
            self.fields['codigo_barras'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_inventario = cleaned_data.get('tipo_inventario')
        
        if tipo_inventario == 'QUINTAL':
            # Validar campos requeridos para quintales
            if not cleaned_data.get('unidad_medida_base'):
                raise ValidationError({
                    'unidad_medida_base': 'Este campo es requerido para productos tipo quintal'
                })
            if not cleaned_data.get('precio_por_unidad_peso'):
                raise ValidationError({
                    'precio_por_unidad_peso': 'Este campo es requerido para productos tipo quintal'
                })
        
        elif tipo_inventario == 'NORMAL':
            # Validar campos requeridos para productos normales
            if not cleaned_data.get('precio_venta'):  # ✅ CORREGIDO
                raise ValidationError({
                    'precio_venta': 'Este campo es requerido para productos normales'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Generar código de barras automáticamente si está marcado
        generar = self.cleaned_data.get('generar_codigo_automatico', False)
        
        if generar and not instance.pk:
            from apps.system_configuration.models import ConfiguracionSistema
            config = ConfiguracionSistema.get_config()
            
            # Generar código secuencial
            ultimo = Producto.objects.filter(
                codigo_barras__startswith=config.prefijo_codigo_producto
            ).order_by('-codigo_barras').first()
            
            if ultimo and ultimo.codigo_barras:
                try:
                    prefijo = config.prefijo_codigo_producto
                    ultimo_num = int(ultimo.codigo_barras.replace(prefijo + '-', ''))
                    siguiente_num = ultimo_num + 1
                except (ValueError, AttributeError):
                    siguiente_num = 1
            else:
                siguiente_num = 1
            
            longitud = config.longitud_codigo_secuencial
            instance.codigo_barras = f"{config.prefijo_codigo_producto}-{siguiente_num:0{longitud}d}"
        
        if commit:
            instance.save()
        
        return instance


# ============================================================================
# FORMULARIOS PARA QUINTALES
# ============================================================================

class QuintalForm(forms.ModelForm):
    """
    Formulario para registrar un nuevo quintal
    ✅ CORREGIDO: Campos según modelo Quintal actual
    """
    
    class Meta:
        model = Quintal
        fields = [
            'producto', 'codigo_quintal', 'peso_inicial', 'unidad_medida',
            'costo_total', 'proveedor', 'fecha_vencimiento'
        ]
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select'
            }),
            'codigo_quintal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CBX-QNT-00001 (auto si vacío)'
            }),
            'peso_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0.001',
                'placeholder': '100.000'
            }),
            'unidad_medida': forms.Select(attrs={
                'class': 'form-select'
            }),
            'costo_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select'
            }),
            'codigo_quintal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CBX-QNT-00001 (auto si vacío)'
            }),
            'peso_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': '100.000'
            }),
            'unidad_medida': forms.Select(attrs={
                'class': 'form-select'
            }),
            'costo_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'numero_factura': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'No. factura del proveedor'
            }),
            'lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de lote'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'ubicacion_almacen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Pasillo 2, Estante A'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos tipo QUINTAL
        self.fields['producto'].queryset = Producto.objects.filter(
            tipo_inventario='QUINTAL',
            activo=True
        )


# ============================================================================
# FORMULARIOS PARA PRODUCTOS NORMALES
# ============================================================================

class ProductoNormalForm(forms.ModelForm):
    """Formulario para gestionar inventario de productos normales"""
    
    class Meta:
        model = ProductoNormal
        fields = [
            'producto', 'stock_actual', 'stock_minimo', 'stock_maximo',
            'costo_unitario', 'lote', 'fecha_vencimiento', 'ubicacion_almacen'
        ]
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select'
            }),
            'stock_actual': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'stock_maximo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'costo_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de lote'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'ubicacion_almacen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Pasillo 3, Estante B'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos tipo NORMAL
        self.fields['producto'].queryset = Producto.objects.filter(
            tipo_inventario='NORMAL',
            activo=True
        )


# ============================================================================
# FORMULARIO DE BÚSQUEDA POR CÓDIGO DE BARRAS
# ============================================================================

class BuscarCodigoBarrasForm(forms.Form):
    """Formulario para buscar productos por código de barras"""
    
    codigo_barras = forms.CharField(
        label='Código de Barras',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Escanea o escribe el código',
            'autofocus': 'autofocus',
            'id': 'input_codigo_barras'
        })
    )


# ============================================================================
# FORMULARIO DE AJUSTE DE INVENTARIO
# ============================================================================

class AjusteInventarioQuintalForm(forms.Form):
    """Formulario para ajustar peso de un quintal"""
    
    quintal = forms.ModelChoiceField(
        queryset=Quintal.objects.filter(estado='DISPONIBLE'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Quintal'
    )
    
    tipo_ajuste = forms.ChoiceField(
        choices=[
            ('AJUSTE_POSITIVO', 'Aumentar peso'),
            ('AJUSTE_NEGATIVO', 'Disminuir peso'),
            ('MERMA', 'Registrar merma')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de Ajuste'
    )
    
    peso_ajuste = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal('0.001'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'placeholder': '0.000'
        }),
        label='Peso a Ajustar'
    )
    
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo del ajuste...'
        }),
        label='Observaciones',
        required=True
    )


class AjusteInventarioNormalForm(forms.Form):
    """Formulario para ajustar stock de producto normal"""
    
    producto_normal = forms.ModelChoiceField(
        queryset=ProductoNormal.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Producto'
    )
    
    tipo_ajuste = forms.ChoiceField(
        choices=[
            ('ENTRADA_AJUSTE', 'Aumentar stock'),
            ('SALIDA_AJUSTE', 'Disminuir stock'),
            ('SALIDA_MERMA', 'Registrar merma/daño')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de Ajuste'
    )
    
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0'
        }),
        label='Cantidad'
    )
    
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo del ajuste...'
        }),
        label='Observaciones',
        required=True
    )


# ============================================================================
# FORMULARIO DE COMPRA
# ============================================================================

class CompraForm(forms.ModelForm):
    """Formulario para registrar una compra"""
    
    class Meta:
        model = Compra
        fields = [
            'numero_compra', 'proveedor', 'numero_factura',
            'fecha_compra', 'descuento', 'impuestos', 'observaciones'
        ]
        widgets = {
            'numero_compra': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'COM-2025-00001'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'numero_factura': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'No. Factura del proveedor'
            }),
            'fecha_compra': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'descuento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'impuestos': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }


# ============================================================================
# FORMSET PARA DETALLES DE COMPRA
# ============================================================================

from django.forms import modelformset_factory

DetalleCompraFormSet = modelformset_factory(
    DetalleCompra,
    fields=[
        'producto', 'peso_comprado', 'unidad_medida',
        'cantidad_unidades', 'costo_unitario'
    ],
    extra=1,
    can_delete=True,
    widgets={
        'producto': forms.Select(attrs={'class': 'form-select'}),
        'peso_comprado': forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001'
        }),
        'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
        'cantidad_unidades': forms.NumberInput(attrs={
            'class': 'form-control'
        }),
        'costo_unitario': forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    }
)