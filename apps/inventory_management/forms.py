# apps/inventory_management/forms.py

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    Categoria, Proveedor, Producto, Quintal,
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
    """Formulario para crear/editar productos (maestro)"""
    
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
            'proveedor', 'tipo_inventario', 'imagen', 'activo',
            # Para quintales
            'unidad_medida_base', 'precio_por_unidad_peso', 'peso_base_quintal',
            # Para normales
            'precio_unitario'
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
                'rows': 3
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tipo_inventario': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_tipo_inventario'
            }),
            'unidad_medida_base': forms.Select(attrs={
                'class': 'form-select'
            }),
            'precio_por_unidad_peso': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'peso_base_quintal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': '100.000'
            }),
            'precio_unitario': forms.NumberInput(attrs={
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
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si es edición, deshabilitar generar automático
        if self.instance and self.instance.pk:
            self.fields['generar_codigo_automatico'].initial = False
            self.fields['codigo_barras'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_inventario = cleaned_data.get('tipo_inventario')
        generar_auto = cleaned_data.get('generar_codigo_automatico')
        
        # Generar código automático si está marcado
        if generar_auto and not self.instance.pk:
            categoria = cleaned_data.get('categoria')
            cleaned_data['codigo_barras'] = BarcodeGenerator.generar_codigo_producto(
                categoria=categoria,
                tipo_inventario=tipo_inventario
            )
        
        # Validar campos según tipo
        if tipo_inventario == 'QUINTAL':
            if not cleaned_data.get('unidad_medida_base'):
                raise ValidationError({
                    'unidad_medida_base': 'La unidad de medida es requerida para quintales'
                })
            if not cleaned_data.get('precio_por_unidad_peso'):
                raise ValidationError({
                    'precio_por_unidad_peso': 'El precio por peso es requerido para quintales'
                })
        
        elif tipo_inventario == 'NORMAL':
            if not cleaned_data.get('precio_unitario'):
                raise ValidationError({
                    'precio_unitario': 'El precio unitario es requerido para productos normales'
                })
        
        return cleaned_data


# ============================================================================
# FORMULARIOS PARA QUINTALES
# ============================================================================

class QuintalForm(forms.ModelForm):
    """Formulario para registrar entrada de quintal"""
    
    generar_codigo_automatico = forms.BooleanField(
        required=False,
        initial=True,
        label='Generar código de quintal automáticamente',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Quintal
        fields = [
            'codigo_unico', 'producto', 'proveedor',
            'peso_inicial', 'unidad_medida', 'costo_total',
            'fecha_recepcion', 'fecha_vencimiento',
            'lote_proveedor', 'numero_factura_compra', 'origen'
        ]
        widgets = {
            'codigo_unico': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CBX-QNT-00001',
                'readonly': 'readonly'
            }),
            'producto': forms.Select(attrs={
                'class': 'form-select'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
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
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'fecha_recepcion': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'lote_proveedor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lote del proveedor'
            }),
            'numero_factura_compra': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'No. Factura'
            }),
            'origen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Origen del producto'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo productos tipo QUINTAL
        self.fields['producto'].queryset = Producto.objects.filter(
            tipo_inventario='QUINTAL',
            activo=True
        )
        
        # Si es edición, no generar automático
        if self.instance and self.instance.pk:
            self.fields['generar_codigo_automatico'].initial = False
            self.fields['codigo_unico'].widget.attrs.pop('readonly', None)
    
    def clean(self):
        cleaned_data = super().clean()
        generar_auto = cleaned_data.get('generar_codigo_automatico')
        
        # Generar código automático si está marcado
        if generar_auto and not self.instance.pk:
            producto = cleaned_data.get('producto')
            cleaned_data['codigo_unico'] = BarcodeGenerator.generar_codigo_quintal(
                producto=producto
            )
        
        # El peso_actual es igual al peso_inicial al crear
        if not self.instance.pk:
            cleaned_data['peso_actual'] = cleaned_data.get('peso_inicial')
        
        return cleaned_data


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