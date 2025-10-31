# apps/financial_management/forms.py

"""
Formularios para el módulo de gestión financiera
Incluye: Cajas, Caja Chica, Cuentas por Cobrar, Cuentas por Pagar
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from .models import (
    Caja, MovimientoCaja, ArqueoCaja,
    CajaChica, MovimientoCajaChica,
    CuentaPorCobrar, PagoCuentaPorCobrar,
    CuentaPorPagar, PagoCuentaPorPagar
)


# ============================================================================
# FORMULARIOS PARA CAJAS
# ============================================================================

class CajaForm(forms.ModelForm):
    """Formulario para crear/editar cajas"""
    
    class Meta:
        model = Caja
        fields = [
            'nombre', 'codigo', 'tipo',
            'requiere_autorizacion_cierre', 'activa'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Caja Principal'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: CJA-001'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'requiere_autorizacion_cierre': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class AperturaCajaForm(forms.Form):
    """Formulario para abrir caja"""
    
    monto_apertura = forms.DecimalField(
        label='Monto de Apertura',
        min_value=Decimal('0.01'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text='Monto inicial con el que se abre la caja'
    )
    observaciones = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones adicionales (opcional)'
        })
    )
    
    def __init__(self, *args, caja=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.caja = caja
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.caja and self.caja.estado == 'ABIERTA':
            raise ValidationError('La caja ya está abierta.')
        
        return cleaned_data


class CierreCajaForm(forms.Form):
    """Formulario para cerrar caja con conteo de efectivo"""
    
    # Billetes
    billetes_100 = forms.IntegerField(
        label='Billetes de $100',
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control billete-input',
            'data-valor': '100'
        })
    )
    billetes_50 = forms.IntegerField(
        label='Billetes de $50',
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control billete-input',
            'data-valor': '50'
        })
    )
    billetes_20 = forms.IntegerField(
        label='Billetes de $20',
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control billete-input',
            'data-valor': '20'
        })
    )
    billetes_10 = forms.IntegerField(
        label='Billetes de $10',
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control billete-input',
            'data-valor': '10'
        })
    )
    billetes_5 = forms.IntegerField(
        label='Billetes de $5',
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control billete-input',
            'data-valor': '5'
        })
    )
    billetes_1 = forms.IntegerField(
        label='Billetes de $1',
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control billete-input',
            'data-valor': '1'
        })
    )
    
    # Monedas
    monedas = forms.DecimalField(
        label='Monedas (Total)',
        initial=Decimal('0.00'),
        min_value=Decimal('0.00'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    # Total contado (se calcula automáticamente con JS)
    monto_contado = forms.DecimalField(
        label='Total Contado',
        min_value=Decimal('0.00'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'id': 'total-contado'
        })
    )
    
    # Observaciones
    observaciones = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones sobre el cierre'
        })
    )
    
    observaciones_diferencia = forms.CharField(
        label='Explicación de Diferencia',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Si hay diferencia, explique el motivo'
        }),
        help_text='Obligatorio si hay diferencia mayor a $1.00'
    )
    
    def __init__(self, *args, caja=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.caja = caja
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.caja and self.caja.estado == 'CERRADA':
            raise ValidationError('La caja ya está cerrada.')
        
        # Validar que si hay diferencia significativa, se explique
        if self.caja:
            monto_contado = cleaned_data.get('monto_contado', Decimal('0'))
            diferencia = abs(monto_contado - self.caja.monto_actual)
            
            if diferencia > Decimal('1.00'):
                if not cleaned_data.get('observaciones_diferencia'):
                    raise ValidationError({
                        'observaciones_diferencia': 'Debe explicar la diferencia de más de $1.00'
                    })
        
        return cleaned_data


class MovimientoCajaForm(forms.ModelForm):
    """Formulario para registrar movimientos manuales de caja"""
    
    class Meta:
        model = MovimientoCaja
        fields = [
            'tipo_movimiento', 'monto', 'observaciones'
        ]
        widgets = {
            'tipo_movimiento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el motivo del movimiento'
            }),
        }
    
    def __init__(self, *args, caja=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.caja = caja
        self.usuario = usuario
        
        # Filtrar tipos de movimiento permitidos manualmente
        self.fields['tipo_movimiento'].choices = [
            choice for choice in self.fields['tipo_movimiento'].choices
            if choice[0] in ['INGRESO', 'RETIRO', 'AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO']
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.caja and self.caja.estado != 'ABIERTA':
            raise ValidationError('No se pueden registrar movimientos en una caja cerrada.')
        
        tipo_movimiento = cleaned_data.get('tipo_movimiento')
        monto = cleaned_data.get('monto')
        
        # Validar que no se retire más de lo que hay
        if tipo_movimiento in ['RETIRO', 'AJUSTE_NEGATIVO']:
            if self.caja and monto > self.caja.monto_actual:
                raise ValidationError({
                    'monto': f'No puede retirar más de lo disponible (${self.caja.monto_actual})'
                })
        
        return cleaned_data


class BuscarMovimientosForm(forms.Form):
    """Formulario para filtrar movimientos"""
    
    fecha_desde = forms.DateField(
        label='Desde',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        label='Hasta',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    tipo_movimiento = forms.ChoiceField(
        label='Tipo de Movimiento',
        required=False,
        choices=[('', 'Todos')] + list(MovimientoCaja.TIPO_MOVIMIENTO_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    usuario = forms.ModelChoiceField(
        label='Usuario',
        required=False,
        queryset=None,  # Se establece en __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Todos'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Importar aquí para evitar import circular
        from apps.authentication.models import Usuario
        self.fields['usuario'].queryset = Usuario.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')


# ============================================================================
# FORMULARIOS PARA CAJA CHICA
# ============================================================================

class CajaChicaForm(forms.ModelForm):
    """Formulario para crear/editar caja chica"""
    
    class Meta:
        model = CajaChica
        fields = [
            'nombre', 'codigo', 'monto_fondo',
            'limite_gasto_individual', 'umbral_reposicion',
            'responsable', 'estado'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Caja Chica Tienda'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: CCH-001'
            }),
            'monto_fondo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'limite_gasto_individual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'umbral_reposicion': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'responsable': forms.Select(attrs={
                'class': 'form-control'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        monto_fondo = cleaned_data.get('monto_fondo')
        umbral_reposicion = cleaned_data.get('umbral_reposicion')
        limite_gasto = cleaned_data.get('limite_gasto_individual')
        
        # Validar que umbral sea menor que fondo
        if umbral_reposicion and monto_fondo:
            if umbral_reposicion >= monto_fondo:
                raise ValidationError({
                    'umbral_reposicion': 'El umbral debe ser menor que el monto del fondo'
                })
        
        # Validar que límite de gasto sea razonable
        if limite_gasto and monto_fondo:
            if limite_gasto > monto_fondo / 2:
                raise ValidationError({
                    'limite_gasto_individual': 'El límite de gasto no debe exceder la mitad del fondo'
                })
        
        return cleaned_data


class GastoCajaChicaForm(forms.Form):
    """Formulario para registrar un gasto de caja chica"""
    
    categoria_gasto = forms.ChoiceField(
        label='Categoría',
        choices=MovimientoCajaChica.CATEGORIA_GASTO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    monto = forms.DecimalField(
        label='Monto',
        min_value=Decimal('0.01'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    descripcion = forms.CharField(
        label='Descripción',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describa el gasto realizado'
        })
    )
    
    numero_comprobante = forms.CharField(
        label='Número de Comprobante',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de factura o recibo'
        })
    )
    
    comprobante_adjunto = forms.FileField(
        label='Comprobante (Imagen/PDF)',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,application/pdf'
        }),
        help_text='Adjunte foto o PDF del comprobante'
    )
    
    def __init__(self, *args, caja_chica=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.caja_chica = caja_chica
        
        if caja_chica:
            self.fields['monto'].help_text = (
                f'Límite por gasto: ${caja_chica.limite_gasto_individual} | '
                f'Disponible: ${caja_chica.monto_actual}'
            )
    
    def clean_monto(self):
        monto = self.cleaned_data['monto']
        
        if self.caja_chica:
            # Validar límite individual
            if monto > self.caja_chica.limite_gasto_individual:
                raise ValidationError(
                    f'El monto excede el límite de ${self.caja_chica.limite_gasto_individual} por gasto'
                )
            
            # Validar fondos disponibles
            if monto > self.caja_chica.monto_actual:
                raise ValidationError(
                    f'Fondos insuficientes. Disponible: ${self.caja_chica.monto_actual}'
                )
        
        return monto


class ReposicionCajaChicaForm(forms.Form):
    """Formulario para reponer el fondo de caja chica"""
    
    monto = forms.DecimalField(
        label='Monto a Reponer',
        min_value=Decimal('0.01'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'readonly': 'readonly'
        }),
        help_text='Este monto se calcula automáticamente'
    )
    
    observaciones = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones sobre la reposición'
        })
    )
    
    def __init__(self, *args, caja_chica=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if caja_chica:
            monto_a_reponer = caja_chica.monto_a_reponer()
            self.fields['monto'].initial = monto_a_reponer
            self.fields['monto'].help_text = (
                f'Fondo: ${caja_chica.monto_fondo} - '
                f'Actual: ${caja_chica.monto_actual} = '
                f'${monto_a_reponer} a reponer'
            )


# ============================================================================
# FORMULARIOS PARA CUENTAS POR COBRAR (CRÉDITOS A CLIENTES)
# ============================================================================

class CuentaPorCobrarForm(forms.ModelForm):
    """Formulario para crear/editar cuenta por cobrar"""
    
    class Meta:
        model = CuentaPorCobrar
        fields = [
            'cliente', 'venta', 'descripcion', 
            'monto_total', 'fecha_vencimiento', 'observaciones'
        ]
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'venta': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la cuenta por cobrar'
            }),
            'monto_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales (opcional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si no hay venta asociada, hacer el campo opcional
        self.fields['venta'].required = False
        
        # Filtrar solo clientes activos con crédito habilitado
        from apps.sales_management.models import Cliente
        self.fields['cliente'].queryset = Cliente.objects.filter(
            activo=True,
            limite_credito__gt=0
        )
    
    def clean_monto_total(self):
        monto = self.cleaned_data.get('monto_total')
        if monto and monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        return monto
    
    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get('cliente')
        monto_total = cleaned_data.get('monto_total')
        
        # Verificar límite de crédito del cliente
        if cliente and monto_total:
            if monto_total > cliente.credito_disponible:
                raise ValidationError(
                    f"El monto (${monto_total}) excede el crédito disponible "
                    f"del cliente (${cliente.credito_disponible})"
                )
        
        return cleaned_data


class RegistrarPagoCuentaPorCobrarForm(forms.ModelForm):
    """Formulario para registrar un pago de cliente"""
    
    class Meta:
        model = PagoCuentaPorCobrar
        fields = [
            'monto', 'metodo_pago', 'numero_comprobante',
            'banco', 'numero_cuenta_banco', 'observaciones'
        ]
        widgets = {
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'metodo_pago': forms.Select(attrs={
                'class': 'form-select'
            }),
            'numero_comprobante': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de comprobante/voucher'
            }),
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del banco'
            }),
            'numero_cuenta_banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cuenta'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones del pago (opcional)'
            })
        }
    
    def __init__(self, *args, cuenta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cuenta = cuenta
        
        # Campos opcionales
        self.fields['numero_comprobante'].required = False
        self.fields['banco'].required = False
        self.fields['numero_cuenta_banco'].required = False
        self.fields['observaciones'].required = False
        
        # Establecer monto máximo al saldo pendiente
        if cuenta:
            self.fields['monto'].widget.attrs['max'] = str(cuenta.saldo_pendiente)
            self.fields['monto'].help_text = f"Saldo pendiente: ${cuenta.saldo_pendiente}"
    
    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        
        if monto and monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        
        if self.cuenta and monto > self.cuenta.saldo_pendiente:
            raise ValidationError(
                f"El monto (${monto}) excede el saldo pendiente (${self.cuenta.saldo_pendiente})"
            )
        
        return monto


class BuscarCuentasPorCobrarForm(forms.Form):
    """Formulario para filtrar cuentas por cobrar"""
    
    cliente = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por cliente...'
        })
    )
    
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los estados')] + CuentaPorCobrar.ESTADO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    solo_vencidas = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


# ============================================================================
# FORMULARIOS PARA CUENTAS POR PAGAR (DEUDAS CON PROVEEDORES)
# ============================================================================

class CuentaPorPagarForm(forms.ModelForm):
    """Formulario para crear/editar cuenta por pagar"""
    
    class Meta:
        model = CuentaPorPagar
        fields = [
            'proveedor', 'numero_factura_proveedor', 'tipo_compra',
            'descripcion', 'monto_total', 'fecha_factura', 
            'fecha_vencimiento', 'observaciones'
        ]
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'numero_factura_proveedor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de factura del proveedor'
            }),
            'tipo_compra': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada de la compra'
            }),
            'monto_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'fecha_factura': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales (opcional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo proveedores activos
        from apps.inventory_management.models import Proveedor
        self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True)
        
        # Establecer fecha actual por defecto si no hay instancia
        if not self.instance.pk:
            self.fields['fecha_factura'].initial = timezone.now().date()
            # Fecha de vencimiento 30 días después por defecto
            self.fields['fecha_vencimiento'].initial = (
                timezone.now().date() + timedelta(days=30)
            )
    
    def clean_monto_total(self):
        monto = self.cleaned_data.get('monto_total')
        if monto and monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        return monto
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_factura = cleaned_data.get('fecha_factura')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento')
        
        # Verificar que fecha de vencimiento sea posterior a fecha de factura
        if fecha_factura and fecha_vencimiento:
            if fecha_vencimiento < fecha_factura:
                raise ValidationError(
                    "La fecha de vencimiento no puede ser anterior a la fecha de factura"
                )
        
        return cleaned_data


class RegistrarPagoCuentaPorPagarForm(forms.ModelForm):
    """Formulario para registrar un pago a proveedor"""
    
    class Meta:
        model = PagoCuentaPorPagar
        fields = [
            'monto', 'metodo_pago', 'numero_comprobante',
            'banco', 'numero_cuenta_banco', 'observaciones'
        ]
        widgets = {
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'metodo_pago': forms.Select(attrs={
                'class': 'form-select'
            }),
            'numero_comprobante': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de comprobante/voucher'
            }),
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del banco'
            }),
            'numero_cuenta_banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cuenta'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones del pago (opcional)'
            })
        }
    
    def __init__(self, *args, cuenta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cuenta = cuenta
        
        # Campos opcionales
        self.fields['numero_comprobante'].required = False
        self.fields['banco'].required = False
        self.fields['numero_cuenta_banco'].required = False
        self.fields['observaciones'].required = False
        
        # Establecer monto máximo al saldo pendiente
        if cuenta:
            self.fields['monto'].widget.attrs['max'] = str(cuenta.saldo_pendiente)
            self.fields['monto'].help_text = f"Saldo pendiente: ${cuenta.saldo_pendiente}"
    
    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        
        if monto and monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        
        if self.cuenta and monto > self.cuenta.saldo_pendiente:
            raise ValidationError(
                f"El monto (${monto}) excede el saldo pendiente (${self.cuenta.saldo_pendiente})"
            )
        
        return monto


class BuscarCuentasPorPagarForm(forms.Form):
    """Formulario para filtrar cuentas por pagar"""
    
    proveedor = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por proveedor...'
        })
    )
    
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los estados')] + CuentaPorPagar.ESTADO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    tipo_compra = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los tipos')] + CuentaPorPagar.TIPO_COMPRA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    solo_vencidas = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )