from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Usuario, Rol, PermisoPersonalizado, SesionUsuario, LogAcceso
from .forms import UsuarioCreationForm, UsuarioChangeForm


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Administración personalizada para usuarios"""
    
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario
    
    list_display = [
        'email', 'codigo_empleado', 'get_full_name', 'rol', 
        'estado', 'is_active', 'fecha_ultimo_acceso', 'intentos_fallidos'
    ]
    list_filter = ['rol', 'estado', 'is_active', 'date_joined']
    search_fields = ['email', 'nombres', 'apellidos', 'codigo_empleado']
    ordering = ['apellidos', 'nombres']
    
    fieldsets = (
        ('Información de autenticación', {
            'fields': ('email', 'username', 'password')
        }),
        ('Información personal', {
            'fields': ('nombres', 'apellidos', 'telefono', 'documento_identidad')
        }),
        ('Información laboral', {
            'fields': ('codigo_empleado', 'rol', 'estado')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas importantes', {
            'fields': ('date_joined', 'fecha_ultimo_acceso', 'fecha_cambio_password')
        }),
        ('Seguridad', {
            'fields': ('intentos_fallidos', 'fecha_bloqueo'),
            'classes': ['collapse']
        }),
    )
    
    add_fieldsets = (
        ('Información de autenticación', {
            'classes': ['wide'],
            'fields': ['email', 'username', 'password1', 'password2']
        }),
        ('Información personal', {
            'fields': ['nombres', 'apellidos', 'telefono', 'documento_identidad']
        }),
        ('Información laboral', {
            'fields': ['codigo_empleado', 'rol']
        }),
    )
    
    readonly_fields = ['date_joined', 'fecha_ultimo_acceso', 'fecha_cambio_password', 'fecha_bloqueo']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nombre completo'
    
    def has_delete_permission(self, request, obj=None):
        # Solo permitir eliminar si no es el usuario actual
        if obj and request.user.id == obj.id:
            return False
        return super().has_delete_permission(request, obj)
    
    actions = ['activar_usuarios', 'desactivar_usuarios', 'reset_intentos_fallidos']
    
    def activar_usuarios(self, request, queryset):
        queryset.update(is_active=True, estado='ACTIVO')
        self.message_user(request, f"{queryset.count()} usuarios activados.")
    activar_usuarios.short_description = "Activar usuarios seleccionados"
    
    def desactivar_usuarios(self, request, queryset):
        # No permitir desactivar el usuario actual
        queryset = queryset.exclude(id=request.user.id)
        queryset.update(is_active=False, estado='INACTIVO')
        self.message_user(request, f"{queryset.count()} usuarios desactivados.")
    desactivar_usuarios.short_description = "Desactivar usuarios seleccionados"
    
    def reset_intentos_fallidos(self, request, queryset):
        queryset.update(intentos_fallidos=0, fecha_bloqueo=None)
        # Cambiar estado de bloqueado a activo si es necesario
        queryset.filter(estado='BLOQUEADO').update(estado='ACTIVO')
        self.message_user(request, f"Intentos fallidos reiniciados para {queryset.count()} usuarios.")
    reset_intentos_fallidos.short_description = "Reiniciar intentos fallidos"


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    """Administración de Roles personalizados"""
    
    list_display = ['nombre', 'codigo', 'is_active', 'created_at', 'get_permissions_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['nombre', 'codigo', 'descripcion']
    ordering = ['nombre']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'descripcion', 'is_active')
        }),
        ('Permisos', {
            'fields': ('permissions',),
            'description': 'Lista de permisos en formato JSON. Ejemplo: ["usuarios.view", "ventas.add"]'
        }),
        ('Metadatos', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_permissions_count(self, obj):
        """Mostrar cantidad de permisos"""
        if obj.permissions:
            return len(obj.permissions)
        return 0
    get_permissions_count.short_description = 'Cantidad de Permisos'
    
    actions = ['activar_roles', 'desactivar_roles']
    
    def activar_roles(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} roles activados.")
    activar_roles.short_description = "Activar roles seleccionados"
    
    def desactivar_roles(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} roles desactivados.")
    desactivar_roles.short_description = "Desactivar roles seleccionados"


@admin.register(PermisoPersonalizado)
class PermisoPersonalizadoAdmin(admin.ModelAdmin):
    """Administración de permisos personalizados"""
    
    list_display = [
        'usuario', 'modulo', 'accion', 'activo', 
        'fecha_asignacion', 'fecha_expiracion'
    ]
    list_filter = ['modulo', 'accion', 'activo', 'fecha_asignacion']
    search_fields = ['usuario__email', 'usuario__nombres', 'usuario__apellidos']
    ordering = ['-fecha_asignacion']
    
    fieldsets = (
        ('Información del permiso', {
            'fields': ('usuario', 'modulo', 'accion', 'activo')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_expiracion')
        }),
    )
    
    readonly_fields = ['fecha_asignacion']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')


@admin.register(SesionUsuario)
class SesionUsuarioAdmin(admin.ModelAdmin):
    """Administración de sesiones de usuario"""
    
    list_display = [
        'usuario', 'ip_address', 'fecha_inicio', 
        'fecha_ultimo_acceso', 'activa', 'user_agent_short'
    ]
    list_filter = ['activa', 'fecha_inicio']
    search_fields = ['usuario__email', 'ip_address']
    ordering = ['-fecha_ultimo_acceso']
    readonly_fields = ['token_session', 'fecha_inicio', 'fecha_ultimo_acceso']
    
    def user_agent_short(self, obj):
        """Mostrar una versión corta del user agent"""
        if len(obj.user_agent) > 50:
            return f"{obj.user_agent[:50]}..."
        return obj.user_agent
    user_agent_short.short_description = 'User Agent'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')
    
    actions = ['cerrar_sesiones']
    
    def cerrar_sesiones(self, request, queryset):
        queryset.update(activa=False)
        self.message_user(request, f"{queryset.count()} sesiones cerradas.")
    cerrar_sesiones.short_description = "Cerrar sesiones seleccionadas"


@admin.register(LogAcceso)
class LogAccesoAdmin(admin.ModelAdmin):
    """Administración de logs de acceso"""
    
    list_display = [
        'usuario', 'email_intento', 'tipo_evento', 'ip_address',
        'fecha_evento', 'exitoso', 'detalles_short'
    ]
    list_filter = [
        'tipo_evento', 'exitoso', 'fecha_evento',
        ('usuario', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'usuario__email', 'email_intento', 'ip_address', 'detalles'
    ]
    ordering = ['-fecha_evento']
    readonly_fields = [
        'usuario', 'email_intento', 'tipo_evento', 'ip_address',
        'user_agent', 'detalles', 'fecha_evento', 'exitoso'
    ]
    
    def detalles_short(self, obj):
        """Mostrar una versión corta de los detalles"""
        if len(obj.detalles) > 50:
            return f"{obj.detalles[:50]}..."
        return obj.detalles
    detalles_short.short_description = 'Detalles'
    
    def has_add_permission(self, request):
        """No permitir agregar logs manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Solo permitir eliminar logs antiguos (opcional)"""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')


# Personalización del sitio de administración
admin.site.site_header = "CommerceBox - Administración"
admin.site.site_title = "CommerceBox Admin"
admin.site.index_title = "Panel de Administración"


# Registro de modelos adicionales si es necesario
from django.contrib.auth.models import Group

# Crear grupos predeterminados
def create_default_groups():
    """Crear grupos predeterminados basados en roles"""
    roles = dict(Usuario.ROLES_CHOICES)
    
    for role_code, role_name in roles.items():
        group, created = Group.objects.get_or_create(name=role_name)
        if created:
            print(f"Grupo creado: {role_name}")

# Esta función se puede llamar en las migraciones o en el setup inicial