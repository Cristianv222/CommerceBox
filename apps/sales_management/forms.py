# apps/sales_management/forms.py

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Cliente, Venta, DetalleVenta, Pago, Devolucion
from apps.inventory_management.models import Producto


# ============================================================================
# FORMULARIOS DE CLIENTE
# ============================================================================

class ClienteForm(forms.ModelForm):
    """Formulario para crear/editar clientes"""
    
    class Meta:
        model = Cliente
        fields = [
            'tipo_documento', 'numero_documento',
            'nombres', 'apellidos', 'nombre_comercial',
            'telefono', 'email', 'direccion',
            'tipo_cliente', 'limite_credito', 'dias_credito',
            'descuento_general', 'activo'
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 0123456789'
            }),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombres del cliente'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellidos del cliente'
            }),
            'nombre_comercial': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de empresa (opcional)'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 0987654321'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección del cliente'
            }),
            'tipo_cliente': forms.Select(attrs={'class': 'form-control'}),
            'limite_credito': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'dias_credito': forms.NumberInput(attrs={'class': 'form-control'}),
            'descuento_general': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_numero_documento(self):
        numero = self.cleaned_data.get('numero_documento')
        tipo = self.cleaned_data.get('tipo_documento')
        
        if tipo == 'CEDULA' and len(numero) != 10:
            raise ValidationError('La cédula debe tener 10 dígitos')
        if tipo == 'RUC' and len(numero) != 13:
            raise ValidationError('El RUC debe tener 13 dígitos')
        
        return numero


class ClienteSearchForm(forms.Form):
    """Formulario de búsqueda rápida de clientes"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, documento...',
            'autofocus': True
        })
    )
    tipo_cliente = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + Cliente.TIPO_CLIENTE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ============================================================================
# FORMULARIOS DE VENTA (POS)
# ============================================================================

class VentaForm(forms.ModelForm):
    """Formulario base para ventas"""
    
    class Meta:
        model = Venta
        fields = [
            'cliente', 'tipo_venta', 'fecha_vencimiento',
            'descuento', 'observaciones'
        ]
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_cliente'
            }),
            'tipo_venta': forms.Select(attrs={'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'descuento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_venta = cleaned_data.get('tipo_venta')
        cliente = cleaned_data.get('cliente')
        
        if tipo_venta == 'CREDITO' and not cliente:
            raise ValidationError('Las ventas a crédito requieren un cliente')
        
        return cleaned_data


class BuscarProductoPOSForm(forms.Form):
    """Formulario para buscar productos en el POS"""
    codigo_barras = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Escanear código de barras o escribir...',
            'autofocus': True,
            'autocomplete': 'off'
        })
    )


class AgregarProductoPOSForm(forms.Form):
    """Formulario para agregar producto al carrito POS"""
    producto_id = forms.UUIDField(widget=forms.HiddenInput())
    
    # Para quintales
    quintal_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    peso_vendido = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'min': '0.001',
            'placeholder': 'Peso'
        })
    )
    
    # Para productos normales
    cantidad_unidades = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'value': '1'
        })
    )
    
    # Precio y descuento
    precio = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'readonly': True
        })
    )
    descuento_porcentaje = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '100',
            'placeholder': '0%'
        })
    )


# ============================================================================
# FORMULARIOS DE PAGO
# ============================================================================

class PagoForm(forms.ModelForm):
    """Formulario para registrar pagos"""
    
    class Meta:
        model = Pago
        fields = ['forma_pago', 'monto', 'numero_referencia', 'banco']
        widgets = {
            'forma_pago': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'numero_referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de autorización, voucher, etc.'
            }),
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del banco'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.venta = kwargs.pop('venta', None)
        super().__init__(*args, **kwargs)
        
        if self.venta:
            saldo = self.venta.saldo_pendiente()
            self.fields['monto'].widget.attrs['max'] = str(saldo)
            self.fields['monto'].initial = saldo
    
    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        
        if self.venta:
            saldo = self.venta.saldo_pendiente()
            if monto > saldo:
                raise ValidationError(
                    f'El monto no puede ser mayor al saldo pendiente (${saldo})'
                )
        
        return monto


class PagoMultipleForm(forms.Form):
    """Formulario para múltiples formas de pago en una venta"""
    efectivo = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    tarjeta_debito = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    tarjeta_credito = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    transferencia = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.total_venta = kwargs.pop('total_venta', Decimal('0'))
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        total_pagado = sum([
            cleaned_data.get('efectivo', Decimal('0')),
            cleaned_data.get('tarjeta_debito', Decimal('0')),
            cleaned_data.get('tarjeta_credito', Decimal('0')),
            cleaned_data.get('transferencia', Decimal('0')),
        ])
        
        if total_pagado < self.total_venta:
            raise ValidationError(
                f'El total pagado (${total_pagado}) es menor al total de la venta (${self.total_venta})'
            )
        
        cleaned_data['total_pagado'] = total_pagado
        cleaned_data['cambio'] = total_pagado - self.total_venta
        
        return cleaned_data


# ============================================================================
# FORMULARIOS DE DEVOLUCIÓN
# ============================================================================

class DevolucionForm(forms.ModelForm):
    """Formulario para registrar devoluciones"""
    
    class Meta:
        model = Devolucion
        fields = [
            'venta_original', 'detalle_venta',
            'cantidad_devuelta', 'motivo', 'descripcion'
        ]
        widgets = {
            'venta_original': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_venta_original'
            }),
            'detalle_venta': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_detalle_venta'
            }),
            'cantidad_devuelta': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0.001'
            }),
            'motivo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el motivo de la devolución...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo ventas completadas
        self.fields['venta_original'].queryset = Venta.objects.filter(
            estado='COMPLETADA'
        ).order_by('-fecha_venta')[:50]


class AprobarDevolucionForm(forms.Form):
    """Formulario para aprobar/rechazar devoluciones"""
    DECISION_CHOICES = [
        ('APROBADA', 'Aprobar'),
        ('RECHAZADA', 'Rechazar'),
    ]
    
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones sobre la decisión...'
        })
    )


# ============================================================================
# FORMULARIOS DE BÚSQUEDA Y FILTROS
# ============================================================================

class VentasFiltroForm(forms.Form):
    """Formulario para filtrar ventas"""
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + Venta.ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tipo_venta = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + Venta.TIPO_VENTA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    vendedor = forms.ModelChoiceField(
        required=False,
        queryset=None,  # Se configura en __init__
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cliente = forms.ModelChoiceField(
        required=False,
        queryset=Cliente.objects.filter(activo=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importar aquí para evitar circular import
        from apps.authentication.models import Usuario
        self.fields['vendedor'].queryset = Usuario.objects.filter(
            activo=True,
            rol__in=['VENDEDOR', 'ADMIN', 'SUPERVISOR']
        )


class ReporteVentasForm(forms.Form):
    """Formulario para generar reportes de ventas"""
    TIPO_REPORTE_CHOICES = [
        ('diario', 'Reporte Diario'),
        ('semanal', 'Reporte Semanal'),
        ('mensual', 'Reporte Mensual'),
        ('personalizado', 'Período Personalizado'),
    ]
    
    tipo_reporte = forms.ChoiceField(
        choices=TIPO_REPORTE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    agrupar_por = forms.ChoiceField(
        choices=[
            ('vendedor', 'Por Vendedor'),
            ('categoria', 'Por Categoría'),
            ('producto', 'Por Producto'),
            ('cliente', 'Por Cliente'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )