from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Usuario, PermisoPersonalizado, LogAcceso


class UsuarioCreationForm(UserCreationForm):
    """Formulario para crear nuevos usuarios"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    nombres = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombres completos'
        })
    )
    apellidos = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellidos completos'
        })
    )
    codigo_empleado = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: EMP001',
            'style': 'text-transform: uppercase;'
        })
    )
    documento_identidad = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de documento'
        })
    )
    telefono = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890'
        })
    )
    rol = forms.ChoiceField(
        choices=Usuario.ROLES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'nombres', 'apellidos', 
            'codigo_empleado', 'documento_identidad', 'telefono', 
            'rol', 'password1', 'password2'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar campos de contraseña
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError('Ya existe un usuario con este email.')
        return email
    
    def clean_codigo_empleado(self):
        codigo = self.cleaned_data.get('codigo_empleado', '').upper()
        if Usuario.objects.filter(codigo_empleado=codigo).exists():
            raise ValidationError('Ya existe un usuario con este código de empleado.')
        return codigo
    
    def clean_documento_identidad(self):
        documento = self.cleaned_data.get('documento_identidad')
        if Usuario.objects.filter(documento_identidad=documento).exists():
            raise ValidationError('Ya existe un usuario con este documento de identidad.')
        return documento
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.nombres = self.cleaned_data['nombres']
        user.apellidos = self.cleaned_data['apellidos']
        user.codigo_empleado = self.cleaned_data['codigo_empleado'].upper()
        user.documento_identidad = self.cleaned_data['documento_identidad']
        user.telefono = self.cleaned_data['telefono']
        user.rol = self.cleaned_data['rol']
        
        if commit:
            user.save()
        return user


class UsuarioChangeForm(UserChangeForm):
    """Formulario para editar usuarios existentes"""
    
    password = None  # Ocultar campo de contraseña
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'nombres', 'apellidos', 
            'telefono', 'rol', 'estado', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LoginForm(forms.Form):
    """Formulario de login personalizado"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Correo electrónico',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            try:
                user = Usuario.objects.get(email=email)
                
                # Verificar si está bloqueado
                if user.esta_bloqueado():
                    raise ValidationError(
                        'Cuenta bloqueada por múltiples intentos fallidos. '
                        'Contacte al administrador.'
                    )
                
                # Verificar estado
                if user.estado != 'ACTIVO':
                    raise ValidationError(f'Usuario {user.estado.lower()}. Contacte al administrador.')
                
                # Autenticar
                self.user_cache = authenticate(
                    self.request,
                    email=email,
                    password=password
                )
                
                if self.user_cache is None:
                    # Incrementar intentos fallidos
                    user.incrementar_intentos_fallidos()
                    raise ValidationError('Email o contraseña incorrectos.')
                else:
                    # Reset intentos fallidos en login exitoso
                    user.reset_intentos_fallidos()
                    
            except Usuario.DoesNotExist:
                raise ValidationError('Email o contraseña incorrectos.')
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache


class CambiarPasswordForm(forms.Form):
    """Formulario para cambiar contraseña"""
    
    password_actual = forms.CharField(
        label='Contraseña actual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña actual'
        })
    )
    password_nueva = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la nueva contraseña'
        })
    )
    password_confirmacion = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la nueva contraseña'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_password_actual(self):
        password_actual = self.cleaned_data.get('password_actual')
        if not self.user.check_password(password_actual):
            raise ValidationError('La contraseña actual es incorrecta.')
        return password_actual
    
    def clean(self):
        cleaned_data = super().clean()
        password_nueva = cleaned_data.get('password_nueva')
        password_confirmacion = cleaned_data.get('password_confirmacion')
        
        if password_nueva and password_confirmacion:
            if password_nueva != password_confirmacion:
                raise ValidationError('Las contraseñas nuevas no coinciden.')
        
        return cleaned_data
    
    def save(self):
        password = self.cleaned_data['password_nueva']
        self.user.set_password(password)
        self.user.fecha_cambio_password = timezone.now()
        self.user.save()
        return self.user


class RecuperarPasswordForm(forms.Form):
    """Formulario para recuperar contraseña"""
    
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            user = Usuario.objects.get(email=email, is_active=True)
            if user.estado != 'ACTIVO':
                raise ValidationError('Su cuenta no está activa. Contacte al administrador.')
        except Usuario.DoesNotExist:
            raise ValidationError('No existe un usuario activo con este correo electrónico.')
        return email


class RestablecerPasswordForm(forms.Form):
    """Formulario para restablecer contraseña con token"""
    
    token = forms.CharField(
        widget=forms.HiddenInput()
    )
    password_nueva = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la nueva contraseña'
        })
    )
    password_confirmacion = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la nueva contraseña'
        })
    )
    
    def clean_token(self):
        token = self.cleaned_data.get('token')
        try:
            user = Usuario.objects.get(
                token_recuperacion=token,
                fecha_expiracion_token__gt=timezone.now()
            )
        except Usuario.DoesNotExist:
            raise ValidationError('Token inválido o expirado.')
        return token
    
    def clean(self):
        cleaned_data = super().clean()
        password_nueva = cleaned_data.get('password_nueva')
        password_confirmacion = cleaned_data.get('password_confirmacion')
        
        if password_nueva and password_confirmacion:
            if password_nueva != password_confirmacion:
                raise ValidationError('Las contraseñas no coinciden.')
        
        return cleaned_data


class PermisoPersonalizadoForm(forms.ModelForm):
    """Formulario para asignar permisos personalizados"""
    
    MODULOS_CHOICES = [
        ('inventory', 'Gestión de Inventario'),
        ('sales', 'Gestión de Ventas'),
        ('financial', 'Gestión Financiera'),
        ('reports', 'Reportes y Análisis'),
        ('notifications', 'Notificaciones'),
        ('system_config', 'Configuración del Sistema'),
    ]
    
    ACCIONES_CHOICES = [
        ('create', 'Crear'),
        ('read', 'Leer'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        ('export', 'Exportar'),
        ('import', 'Importar'),
        ('approve', 'Aprobar'),
        ('configure', 'Configurar'),
    ]
    
    modulo = forms.ChoiceField(
        choices=MODULOS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    accion = forms.ChoiceField(
        choices=ACCIONES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_expiracion = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    
    class Meta:
        model = PermisoPersonalizado
        fields = ['usuario', 'modulo', 'accion', 'fecha_expiracion']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo usuarios activos
        self.fields['usuario'].queryset = Usuario.objects.filter(
            is_active=True,
            estado='ACTIVO'
        ).order_by('apellidos', 'nombres')


class FiltroUsuariosForm(forms.Form):
    """Formulario para filtrar usuarios"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, email o código...'
        })
    )
    rol = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los roles')] + Usuario.ROLES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los estados')] + Usuario.ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('True', 'Activos'),
            ('False', 'Inactivos')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FiltroLogsForm(forms.Form):
    """Formulario para filtrar logs de acceso"""
    
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.all(),
        required=False,
        empty_label='Todos los usuarios',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tipo_evento = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los eventos')] + LogAcceso.TIPO_EVENTO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
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
    ip_address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'IP específica...'
        })
    )