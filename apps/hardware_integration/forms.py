# apps/hardware_integration/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Impresora, PlantillaImpresion, ConfiguracionCodigoBarras,
    GavetaDinero, EscanerCodigoBarras
)
import json


class ImpresoraForm(forms.ModelForm):
    class Meta:
        model = Impresora
        fields = '__all__'  # Incluye TODOS los campos del modelo
        widgets = {
            # Identificación
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Tipo y conexión
            'tipo_impresora': forms.Select(attrs={'class': 'form-control'}),
            'tipo_conexion': forms.Select(attrs={'class': 'form-control'}),
            'protocolo': forms.Select(attrs={'class': 'form-control'}),
            
            # Conexión USB
            'puerto_usb': forms.TextInput(attrs={'class': 'form-control'}),
            'vid_usb': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 0x04b8'}),
            'pid_usb': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 0x0e15'}),
            
            # Conexión Red
            'direccion_ip': forms.TextInput(attrs={'class': 'form-control'}),
            'puerto_red': forms.NumberInput(attrs={'class': 'form-control'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Conexión Serial
            'puerto_serial': forms.TextInput(attrs={'class': 'form-control'}),
            'baudrate': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Driver
            'nombre_driver': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Papel y etiquetas
            'ancho_papel': forms.NumberInput(attrs={'class': 'form-control'}),
            'largo_maximo': forms.NumberInput(attrs={'class': 'form-control'}),
            'ancho_etiqueta': forms.NumberInput(attrs={'class': 'form-control'}),
            'alto_etiqueta': forms.NumberInput(attrs={'class': 'form-control'}),
            'gap_etiquetas': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Configuración de impresión
            'densidad_impresion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'velocidad_impresion': forms.NumberInput(attrs={'class': 'form-control', 'min': 50, 'max': 300}),
            
            # Capacidades (checkboxes)
            'soporta_corte_automatico': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_corte_parcial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_codigo_barras': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_qr': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_imagenes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Gaveta
            'tiene_gaveta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pin_gaveta': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 1}),
            
            # Estado y ubicación
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Configuración extra (JSON)
            'configuracion_extra': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            
            # Uso predeterminado
            'es_principal_tickets': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_principal_facturas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_principal_etiquetas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Notas
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo_conexion = cleaned_data.get('tipo_conexion')
        tipo_impresora = cleaned_data.get('tipo_impresora')

        # Validación de conexión
        if tipo_conexion == 'USB' and not cleaned_data.get('puerto_usb'):
            self.add_error('puerto_usb', 'Este campo es requerido para conexión USB.')
        
        if tipo_conexion in ['LAN', 'WIFI'] and not cleaned_data.get('direccion_ip'):
            self.add_error('direccion_ip', 'Este campo es requerido para conexión de red.')
        
        if tipo_conexion == 'SERIAL' and not cleaned_data.get('puerto_serial'):
            self.add_error('puerto_serial', 'Este campo es requerido para conexión serial.')
        
        if tipo_conexion == 'DRIVER' and not cleaned_data.get('nombre_driver'):
            self.add_error('nombre_driver', 'Este campo es requerido para conexión por driver.')
        
        # Validación de etiquetas
        if tipo_impresora == 'ETIQUETAS':
            if not cleaned_data.get('ancho_etiqueta'):
                self.add_error('ancho_etiqueta', 'Requerido para impresoras de etiquetas.')
            if not cleaned_data.get('alto_etiqueta'):
                self.add_error('alto_etiqueta', 'Requerido para impresoras de etiquetas.')
        
        # Validación JSON
        configuracion_extra = cleaned_data.get('configuracion_extra')
        if configuracion_extra:
            try:
                json.loads(configuracion_extra)
            except (ValueError, TypeError):
                self.add_error('configuracion_extra', 'Debe ser un JSON válido.')

        return cleaned_data


class PlantillaImpresionForm(forms.ModelForm):
    class Meta:
        model = PlantillaImpresion
        fields = '__all__'
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'formato': forms.Select(attrs={'class': 'form-control'}),
            'impresora': forms.Select(attrs={'class': 'form-control'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'variables_disponibles': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'incluye_logo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluye_encabezado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluye_pie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'margen_superior': forms.NumberInput(attrs={'class': 'form-control'}),
            'margen_inferior': forms.NumberInput(attrs={'class': 'form-control'}),
            'margen_izquierdo': forms.NumberInput(attrs={'class': 'form-control'}),
            'margen_derecho': forms.NumberInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_predeterminada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_variables_disponibles(self):
        data = self.cleaned_data['variables_disponibles']
        if data:
            try:
                parsed = json.loads(data)
                if not isinstance(parsed, list):
                    raise ValidationError('Debe ser una lista de variables.')
                return data
            except (ValueError, TypeError):
                raise ValidationError('Debe ser un JSON válido (lista).')
        return data


class ConfiguracionCodigoBarrasForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionCodigoBarras
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_codigo': forms.Select(attrs={'class': 'form-control'}),
            'prefijo': forms.TextInput(attrs={'class': 'form-control'}),
            'sufijo': forms.TextInput(attrs={'class': 'form-control'}),
            'longitud_secuencia': forms.NumberInput(attrs={'class': 'form-control', 'min': 3, 'max': 10}),
            'ultimo_numero': forms.NumberInput(attrs={'class': 'form-control'}),
            'ancho_codigo': forms.NumberInput(attrs={'class': 'form-control'}),
            'alto_codigo': forms.NumberInput(attrs={'class': 'form-control'}),
            'mostrar_texto': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'posicion_texto': forms.Select(attrs={'class': 'form-control'}),
            'tamaño_fuente': forms.NumberInput(attrs={'class': 'form-control', 'min': 6, 'max': 20}),
            'incluye_nombre_producto': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluye_precio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluye_fecha': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluye_marca': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_para_productos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_para_quintales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_predeterminada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class GavetaDineroForm(forms.ModelForm):
    class Meta:
        model = GavetaDinero
        fields = '__all__'
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_conexion': forms.Select(attrs={'class': 'form-control'}),
            'impresora': forms.Select(attrs={'class': 'form-control'}),
            'puerto': forms.TextInput(attrs={'class': 'form-control'}),
            'comando_apertura': forms.TextInput(attrs={'class': 'form-control'}),
            'duracion_pulso': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'abrir_en_venta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'abrir_en_cobro': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requiere_autorizacion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class EscanerCodigoBarrasForm(forms.ModelForm):
    class Meta:
        model = EscanerCodigoBarras
        fields = '__all__'
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_escaner': forms.Select(attrs={'class': 'form-control'}),
            'modo_operacion': forms.Select(attrs={'class': 'form-control'}),
            'prefijo': forms.TextInput(attrs={'class': 'form-control'}),
            'sufijo': forms.TextInput(attrs={'class': 'form-control'}),
            'soporta_ean13': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_ean8': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_upc': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_code128': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_code39': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_qr': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'soporta_datamatrix': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
        }


class TestImpresionForm(forms.Form):
    TIPO_PRUEBA_CHOICES = [
        ('PAGINA', 'Página de prueba'),
        ('TICKET', 'Ticket de venta'),
        ('ETIQUETA', 'Etiqueta de producto'),
    ]
    
    tipo_prueba = forms.ChoiceField(
        choices=TIPO_PRUEBA_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Selecciona el tipo de prueba"
    )


# ========================
# FORMULARIOS ESPECIALES
# ========================

class MantenimientoImpresoraForm(forms.Form):
    """Formulario para registrar mantenimiento"""
    reset_contador = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Reiniciar contador de impresiones"
    )
    notas_mantenimiento = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Notas del mantenimiento"
    )


class ConfiguracionGavetaForm(forms.ModelForm):
    """Formulario simplificado para configurar gaveta desde impresora"""
    class Meta:
        model = GavetaDinero
        fields = ['nombre', 'ubicacion', 'requiere_autorizacion', 'abrir_en_venta']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'requiere_autorizacion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'abrir_en_venta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }