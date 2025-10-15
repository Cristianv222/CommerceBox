# apps/system_configuration/forms.py

"""
Formularios para configuración del sistema
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import (
    ConfiguracionSistema, ParametroSistema, 
    RegistroBackup, LogConfiguracion
)


# ============================================================================
# FORMULARIO DE CONFIGURACIÓN GENERAL
# ============================================================================

class ConfiguracionSistemaForm(forms.ModelForm):
    """Formulario para configuración general del sistema"""
    
    class Meta:
        model = ConfiguracionSistema
        fields = [
            # Información general
            'nombre_empresa', 'ruc_empresa', 'direccion_empresa',
            'telefono_empresa', 'email_empresa', 'sitio_web',
            'logo_empresa',  # ✅ AGREGADO
            
            # Inventario
            'prefijo_codigo_quintal', 'prefijo_codigo_producto',
            'longitud_codigo_secuencial', 'umbral_stock_critico_porcentaje',
            'umbral_stock_bajo_porcentaje', 'stock_minimo_default',
            'dias_alerta_vencimiento', 'peso_minimo_quintal_critico',
            
            # Ventas
            'prefijo_numero_factura', 'prefijo_numero_venta',
            'iva_default', 'max_descuento_sin_autorizacion',
            'permitir_ventas_credito', 'dias_credito_default',
            
            # Financiero
            'moneda', 'simbolo_moneda', 'decimales_moneda',
            'monto_inicial_caja', 'monto_fondo_caja_chica',
            'alerta_diferencia_caja',
            
            # Facturación electrónica
            'facturacion_electronica_activa', 'ambiente_facturacion',
            
            # Notificaciones
            'notificaciones_email_activas', 'email_notificaciones',
            'notificar_stock_bajo', 'notificar_vencimientos',
            'notificar_cierre_caja',
            
            # Backups
            'backup_automatico_activo', 'frecuencia_backup',
            'hora_backup', 'dias_retencion_backup', 'ruta_backup',
            
            # Sistema
            'mantenimiento_activo', 'mensaje_mantenimiento',
            'activar_logs_detallados', 'dias_retencion_logs',
            
            # Seguridad
            'timeout_sesion', 'intentos_login_maximos',
            'tiempo_bloqueo_cuenta',
            
            # Interfaz
            'tema_interfaz', 'idioma', 'zona_horaria',
            'formato_fecha', 'formato_hora',
            
            # Módulos
            'modulo_inventario_activo', 'modulo_ventas_activo',
            'modulo_financiero_activo', 'modulo_reportes_activo',
            'modulo_alertas_activo',
        ]
        widgets = {
            # Información general
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa'
            }),
            'ruc_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890001'
            }),
            'direccion_empresa': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'telefono_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+593 XXX XXXX'
            }),
            'email_empresa': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'sitio_web': forms.URLInput(attrs={
                'class': 'form-control'
            }),
            
            # ✅ NUEVO: Widget para el logo
            'logo_empresa': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            
            # Inventario
            'prefijo_codigo_quintal': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'prefijo_codigo_producto': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'longitud_codigo_secuencial': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'umbral_stock_critico_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'umbral_stock_bajo_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'stock_minimo_default': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'dias_alerta_vencimiento': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'peso_minimo_quintal_critico': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001'
            }),
            
            # Ventas
            'prefijo_numero_factura': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'prefijo_numero_venta': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'iva_default': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_descuento_sin_autorizacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'permitir_ventas_credito': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'dias_credito_default': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            
            # Financiero
            'moneda': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'simbolo_moneda': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'decimales_moneda': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'monto_inicial_caja': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'monto_fondo_caja_chica': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'alerta_diferencia_caja': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            
            # Facturación electrónica
            'facturacion_electronica_activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ambiente_facturacion': forms.Select(attrs={
                'class': 'form-control'
            }),
            
            # Notificaciones
            'notificaciones_email_activas': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'email_notificaciones': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'notificar_stock_bajo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notificar_vencimientos': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notificar_cierre_caja': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            # Backups
            'backup_automatico_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'frecuencia_backup': forms.Select(attrs={
                'class': 'form-control'
            }),
            'hora_backup': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'dias_retencion_backup': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'ruta_backup': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            
            # Sistema
            'mantenimiento_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mensaje_mantenimiento': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'activar_logs_detallados': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'dias_retencion_logs': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            
            # Seguridad
            'timeout_sesion': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'intentos_login_maximos': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'tiempo_bloqueo_cuenta': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            
            # Interfaz
            'tema_interfaz': forms.Select(attrs={
                'class': 'form-control'
            }),
            'idioma': forms.Select(attrs={
                'class': 'form-control'
            }),
            'zona_horaria': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'formato_fecha': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'formato_hora': forms.Select(attrs={
                'class': 'form-control'
            }),
            
            # Módulos
            'modulo_inventario_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'modulo_ventas_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'modulo_financiero_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'modulo_reportes_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'modulo_alertas_activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# ============================================================================
# FORMULARIO DE PARÁMETROS
# ============================================================================

class ParametroSistemaForm(forms.ModelForm):
    """Formulario para parámetros del sistema"""
    
    class Meta:
        model = ParametroSistema
        fields = [
            'modulo', 'clave', 'nombre', 'descripcion',
            'tipo_dato', 'valor', 'valor_default',
            'requerido', 'editable', 'grupo', 'orden', 'activo'
        ]
        widgets = {
            'modulo': forms.TextInput(attrs={'class': 'form-control'}),
            'clave': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo_dato': forms.Select(attrs={'class': 'form-control'}),
            'valor': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'valor_default': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requerido': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'editable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'grupo': forms.TextInput(attrs={'class': 'form-control'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ============================================================================
# FORMULARIO DE BACKUP
# ============================================================================

class EjecutarBackupForm(forms.Form):
    """Formulario para ejecutar backup manual"""
    
    TIPO_BACKUP_CHOICES = [
        ('COMPLETO', 'Backup Completo'),
        ('MANUAL', 'Backup Manual'),
    ]
    
    tipo_backup = forms.ChoiceField(
        choices=TIPO_BACKUP_CHOICES,
        initial='MANUAL',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    incluir_media = forms.BooleanField(
        required=False,
        initial=True,
        label='Incluir archivos media',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    comprimir = forms.BooleanField(
        required=False,
        initial=True,
        label='Comprimir backup',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones sobre este backup...'
        })
    )


# ============================================================================
# FORMULARIOS DE BÚSQUEDA
# ============================================================================

class LogConfiguracionFiltroForm(forms.Form):
    """Formulario para filtrar logs de configuración"""
    
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
    tabla = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tabla...'
        })
    )
    tipo_cambio = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + LogConfiguracion.TIPO_CAMBIO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class BackupFiltroForm(forms.Form):
    """Formulario para filtrar backups"""
    
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + RegistroBackup.ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tipo_backup = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + RegistroBackup.TIPO_BACKUP_CHOICES,
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