from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid


class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario"""
    
    def create_user(self, username, email, password=None, **extra_fields):
        """Crear y guardar un usuario regular"""
        if not username:
            raise ValueError('El username es obligatorio')
        if not email:
            raise ValueError('El email es obligatorio')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """Crear y guardar un superusuario"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'ADMIN')
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo personalizado de usuario con roles específicos del sistema"""
    
    ROLES_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('SUPERVISOR', 'Supervisor'),
        ('VENDEDOR', 'Vendedor'),
        ('CAJERO', 'Cajero'),
    ]
    
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('SUSPENDIDO', 'Suspendido'),
        ('BLOQUEADO', 'Bloqueado'),
    ]
    
    # Identificadores únicos
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_empleado = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[RegexValidator(r'^[A-Z0-9]{4,10}$', 'Formato: 4-10 caracteres alfanuméricos en mayúsculas')]
    )
    
    # Información de autenticación
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    username = models.CharField(max_length=30, unique=True, verbose_name='Nombre de usuario')
    
    # Información personal
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    telefono = models.CharField(
        max_length=15, 
        blank=True, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Formato de teléfono inválido')]
    )
    documento_identidad = models.CharField(max_length=20, unique=True, verbose_name='Documento de identidad')
    
    # Rol y permisos
    rol = models.CharField(max_length=20, choices=ROLES_CHOICES, default='VENDEDOR')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    
    # Control de acceso
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Fechas importantes
    date_joined = models.DateTimeField(default=timezone.now)
    fecha_ultimo_acceso = models.DateTimeField(null=True, blank=True)
    fecha_cambio_password = models.DateTimeField(default=timezone.now)
    
    # Seguridad
    intentos_fallidos = models.PositiveIntegerField(default=0)
    fecha_bloqueo = models.DateTimeField(null=True, blank=True)
    token_recuperacion = models.CharField(max_length=100, blank=True)
    fecha_expiracion_token = models.DateTimeField(null=True, blank=True)
    
    # Configuración del modelo
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'nombres', 'apellidos', 'codigo_empleado']
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        db_table = 'auth_usuario'
        ordering = ['apellidos', 'nombres']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.codigo_empleado})"
    
    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        return f"{self.nombres} {self.apellidos}".strip()
    
    def get_short_name(self):
        """Retorna el primer nombre del usuario"""
        return self.nombres.split()[0] if self.nombres else self.username
    
    def is_admin(self):
        """Verifica si el usuario es administrador"""
        return self.rol == 'ADMIN'
    
    def is_supervisor(self):
        """Verifica si el usuario es supervisor"""
        return self.rol in ['ADMIN', 'SUPERVISOR']
    
    def is_vendedor(self):
        """Verifica si el usuario puede realizar ventas"""
        return self.rol in ['ADMIN', 'SUPERVISOR', 'VENDEDOR']
    
    def is_cajero(self):
        """Verifica si el usuario puede manejar caja"""
        return self.rol in ['ADMIN', 'SUPERVISOR', 'CAJERO']
    
    def puede_acceder_modulo(self, modulo):
        """Verifica si el usuario puede acceder a un módulo específico"""
        permisos_por_rol = {
            'ADMIN': ['todos'],
            'SUPERVISOR': ['inventory', 'sales', 'financial', 'reports', 'notifications'],
            'VENDEDOR': ['inventory', 'sales'],
            'CAJERO': ['sales', 'financial'],
        }
        
        permisos = permisos_por_rol.get(self.rol, [])
        return 'todos' in permisos or modulo in permisos
    
    def incrementar_intentos_fallidos(self):
        """Incrementa el contador de intentos fallidos"""
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= 5:
            self.estado = 'BLOQUEADO'
            self.fecha_bloqueo = timezone.now()
        self.save()
    
    def reset_intentos_fallidos(self):
        """Reinicia el contador de intentos fallidos"""
        self.intentos_fallidos = 0
        if self.estado == 'BLOQUEADO':
            self.estado = 'ACTIVO'
            self.fecha_bloqueo = None
        self.save()
    
    def esta_bloqueado(self):
        """Verifica si el usuario está bloqueado"""
        return self.estado == 'BLOQUEADO' or self.intentos_fallidos >= 5


class PermisoPersonalizado(models.Model):
    """Permisos personalizados que se pueden asignar a usuarios específicos"""
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='permisos_personalizados')
    modulo = models.CharField(max_length=50)
    accion = models.CharField(max_length=50)  # create, read, update, delete, export, etc.
    activo = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(default=timezone.now)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Permiso personalizado'
        verbose_name_plural = 'Permisos personalizados'
        unique_together = ['usuario', 'modulo', 'accion']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.modulo}.{self.accion}"


class SesionUsuario(models.Model):
    """Registro de sesiones activas de usuarios"""
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sesiones')
    token_session = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_ultimo_acceso = models.DateTimeField(default=timezone.now)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Sesión de usuario'
        verbose_name_plural = 'Sesiones de usuario'
        ordering = ['-fecha_ultimo_acceso']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.fecha_inicio}"


class LogAcceso(models.Model):
    """Log de accesos y actividades del sistema"""
    
    TIPO_EVENTO_CHOICES = [
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('LOGIN_FAILED', 'Intento de inicio fallido'),
        ('PASSWORD_CHANGE', 'Cambio de contraseña'),
        ('ACCOUNT_LOCKED', 'Cuenta bloqueada'),
        ('PERMISSION_DENIED', 'Permiso denegado'),
    ]
    
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    email_intento = models.EmailField(null=True, blank=True)  # Para intentos fallidos
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    detalles = models.TextField(blank=True)
    fecha_evento = models.DateTimeField(default=timezone.now)
    exitoso = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Log de acceso'
        verbose_name_plural = 'Logs de acceso'
        ordering = ['-fecha_evento']
        indexes = [
            models.Index(fields=['usuario', 'fecha_evento']),
            models.Index(fields=['tipo_evento', 'fecha_evento']),
            models.Index(fields=['ip_address', 'fecha_evento']),
        ]
    
    def __str__(self):
        usuario_str = self.usuario.get_full_name() if self.usuario else self.email_intento
        return f"{usuario_str} - {self.get_tipo_evento_display()} - {self.fecha_evento}"

class Rol(models.Model):
    """Modelo para gestión dinámica de roles"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre del rol')
    codigo = models.CharField(max_length=20, unique=True, verbose_name='Código del rol')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    permissions = models.JSONField(default=list, verbose_name='Permisos asignados')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        db_table = 'auth_rol'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"