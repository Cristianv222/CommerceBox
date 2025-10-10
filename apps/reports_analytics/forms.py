# apps/reports_analytics/forms.py

from django import forms
from django.utils import timezone
from datetime import timedelta

from apps.inventory_management.models import Categoria, Proveedor, Producto
from apps.authentication.models import Usuario


class FiltroFechasForm(forms.Form):
    """
    Formulario base para filtros de fechas
    """
    fecha_desde = forms.DateField(
        label='Desde',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
    )
    fecha_hasta = forms.DateField(
        label='Hasta',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Valores por defecto: último mes
        if not self.is_bound:
            hoy = timezone.now().date()
            self.initial['fecha_hasta'] = hoy
            self.initial['fecha_desde'] = hoy - timedelta(days=30)
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_desde = cleaned_data.get('fecha_desde')
        fecha_hasta = cleaned_data.get('fecha_hasta')
        
        if fecha_desde and fecha_hasta:
            if fecha_desde > fecha_hasta:
                raise forms.ValidationError(
                    'La fecha "Desde" no puede ser posterior a la fecha "Hasta"'
                )
            
            # Validar que no sea más de 1 año
            if (fecha_hasta - fecha_desde).days > 365:
                raise forms.ValidationError(
                    'El rango de fechas no puede ser mayor a 1 año'
                )
        
        return cleaned_data


class FiltroVentasForm(FiltroFechasForm):
    """
    Filtros para reportes de ventas
    """
    TIPO_VENTA_CHOICES = [
        ('', 'Todos'),
        ('CONTADO', 'Contado'),
        ('CREDITO', 'Crédito'),
    ]
    
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(activa=True),
        required=False,
        empty_label='Todas las categorías',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vendedor = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol__codigo__in=['ADMIN', 'SUPERVISOR']),
        required=False,
        empty_label='Todos los vendedores',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    tipo_venta = forms.ChoiceField(
        choices=TIPO_VENTA_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    tipo_producto = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('QUINTAL', 'Solo Quintales'),
            ('NORMAL', 'Solo Productos Normales'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FiltroInventarioForm(forms.Form):
    """
    Filtros para reportes de inventario
    """
    TIPO_PRODUCTO_CHOICES = [
        ('TODOS', 'Todos'),
        ('QUINTAL', 'Quintales'),
        ('NORMAL', 'Productos Normales'),
    ]
    
    ESTADO_CHOICES = [
        ('TODOS', 'Todos'),
        ('DISPONIBLE', 'Disponible'),
        ('CRITICO', 'Crítico'),
        ('AGOTADO', 'Agotado'),
    ]
    
    tipo_producto = forms.ChoiceField(
        choices=TIPO_PRODUCTO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='TODOS'
    )
    
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(activa=True),
        required=False,
        empty_label='Todas las categorías',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(activo=True),
        required=False,
        empty_label='Todos los proveedores',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='TODOS'
    )


class FiltroFinancieroForm(FiltroFechasForm):
    """
    Filtros para reportes financieros
    """
    from apps.financial_management.models import Caja
    
    caja = forms.ModelChoiceField(
        queryset=Caja.objects.filter(activa=True),
        required=False,
        empty_label='Todas las cajas',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    incluir_caja_chica = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class FiltroTrazabilidadForm(forms.Form):
    """
    Filtros para reportes de trazabilidad
    """
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(
            tipo_inventario='QUINTAL',
            activo=True
        ),
        required=False,
        empty_label='Todos los productos',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(activo=True),
        required=False,
        empty_label='Todos los proveedores',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    lote = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de lote'
        })
    )
    
    codigo_quintal = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Código de quintal (CBX-QNT-XXXXX)'
        })
    )


class PeriodoRapidoForm(forms.Form):
    """
    Selección rápida de períodos predefinidos
    """
    PERIODO_CHOICES = [
        ('HOY', 'Hoy'),
        ('AYER', 'Ayer'),
        ('SEMANA', 'Esta semana'),
        ('MES', 'Este mes'),
        ('MES_ANTERIOR', 'Mes anterior'),
        ('TRIMESTRE', 'Este trimestre'),
        ('ANIO', 'Este año'),
        ('PERSONALIZADO', 'Personalizado'),
    ]
    
    periodo = forms.ChoiceField(
        choices=PERIODO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='MES'
    )
    
    def get_fechas(self):
        """
        Retorna tupla (fecha_desde, fecha_hasta) según el período seleccionado
        """
        periodo = self.cleaned_data.get('periodo')
        hoy = timezone.now().date()
        
        if periodo == 'HOY':
            return (hoy, hoy)
        
        elif periodo == 'AYER':
            ayer = hoy - timedelta(days=1)
            return (ayer, ayer)
        
        elif periodo == 'SEMANA':
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            return (inicio_semana, hoy)
        
        elif periodo == 'MES':
            inicio_mes = hoy.replace(day=1)
            return (inicio_mes, hoy)
        
        elif periodo == 'MES_ANTERIOR':
            primer_dia_mes = hoy.replace(day=1)
            ultimo_dia_mes_anterior = primer_dia_mes - timedelta(days=1)
            primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
            return (primer_dia_mes_anterior, ultimo_dia_mes_anterior)
        
        elif periodo == 'TRIMESTRE':
            mes_actual = hoy.month
            inicio_trimestre = hoy.replace(month=((mes_actual-1)//3)*3 + 1, day=1)
            return (inicio_trimestre, hoy)
        
        elif periodo == 'ANIO':
            inicio_anio = hoy.replace(month=1, day=1)
            return (inicio_anio, hoy)
        
        else:  # PERSONALIZADO
            return None


class ExportarReporteForm(forms.Form):
    """
    Formulario para exportar reportes
    """
    FORMATO_CHOICES = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
    ]
    
    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='PDF'
    )
    
    incluir_graficos = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Incluir gráficos en el reporte (solo para PDF)'
    )
    
    guardar_reporte = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Guardar este reporte para consulta posterior'
    )


class ConfiguracionDashboardForm(forms.Form):
    """
    Configuración de widgets del dashboard
    """
    mostrar_ventas_dia = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    mostrar_inventario = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    mostrar_alertas = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    mostrar_top_productos = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    mostrar_graficos = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    limite_top_productos = forms.IntegerField(
        min_value=5,
        max_value=50,
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )