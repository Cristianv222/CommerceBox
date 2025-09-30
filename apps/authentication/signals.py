from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.utils import timezone
from .models import Usuario, LogAcceso, SesionUsuario
from .decorators import get_client_ip


@receiver(post_save, sender=Usuario)
def usuario_post_save(sender, instance, created, **kwargs):
    """Signal que se ejecuta después de guardar un usuario"""
    if created:
        # Log de creación de usuario
        LogAcceso.objects.create(
            usuario=instance,
            tipo_evento='USER_CREATED',
            ip_address='127.0.0.1',  # Sistema
            user_agent='Sistema',
            detalles=f'Usuario creado: {instance.get_full_name()} ({instance.codigo_empleado})',
            exitoso=True
        )
        
        # Asignar al grupo correspondiente según el rol
        from django.contrib.auth.models import Group
        try:
            group_name = dict(Usuario.ROLES_CHOICES)[instance.rol]
            group, created = Group.objects.get_or_create(name=group_name)
            instance.groups.add(group)
        except Exception:
            pass  # Ignorar errores de grupos


@receiver(pre_save, sender=Usuario)
def usuario_pre_save(sender, instance, **kwargs):
    """Signal que se ejecuta antes de guardar un usuario"""
    if instance.pk:  # Solo para usuarios existentes
        try:
            original = Usuario.objects.get(pk=instance.pk)
            
            # Detectar cambios de estado
            if original.estado != instance.estado:
                LogAcceso.objects.create(
                    usuario=instance,
                    tipo_evento='USER_STATUS_CHANGED',
                    ip_address='127.0.0.1',
                    user_agent='Sistema',
                    detalles=f'Estado cambiado de {original.estado} a {instance.estado}',
                    exitoso=True
                )
                
                # Si se bloquea el usuario, cerrar sus sesiones
                if instance.estado == 'BLOQUEADO':
                    SesionUsuario.objects.filter(
                        usuario=instance,
                        activa=True
                    ).update(activa=False)
            
            # Detectar cambios de rol
            if original.rol != instance.rol:
                LogAcceso.objects.create(
                    usuario=instance,
                    tipo_evento='USER_ROLE_CHANGED',
                    ip_address='127.0.0.1',
                    user_agent='Sistema',
                    detalles=f'Rol cambiado de {original.rol} a {instance.rol}',
                    exitoso=True
                )
                
                # Actualizar grupos
                from django.contrib.auth.models import Group
                try:
                    # Remover del grupo anterior
                    old_group_name = dict(Usuario.ROLES_CHOICES)[original.rol]
                    old_group = Group.objects.get(name=old_group_name)
                    instance.groups.remove(old_group)
                    
                    # Agregar al nuevo grupo
                    new_group_name = dict(Usuario.ROLES_CHOICES)[instance.rol]
                    new_group, created = Group.objects.get_or_create(name=new_group_name)
                    instance.groups.add(new_group)
                except Exception:
                    pass
                    
        except Usuario.DoesNotExist:
            pass  # Usuario nuevo


@receiver(post_delete, sender=Usuario)
def usuario_post_delete(sender, instance, **kwargs):
    """Signal que se ejecuta después de eliminar un usuario"""
    LogAcceso.objects.create(
        email_intento=instance.email,
        tipo_evento='USER_DELETED',
        ip_address='127.0.0.1',
        user_agent='Sistema',
        detalles=f'Usuario eliminado: {instance.get_full_name()} ({instance.codigo_empleado})',
        exitoso=True
    )


@receiver(user_logged_in)
def usuario_logged_in(sender, request, user, **kwargs):
    """Signal que se ejecuta cuando un usuario inicia sesión"""
    # Actualizar último acceso
    user.fecha_ultimo_acceso = timezone.now()
    user.save(update_fields=['fecha_ultimo_acceso'])
    
    # Crear registro de log
    LogAcceso.objects.create(
        usuario=user,
        tipo_evento='LOGIN',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        detalles='Login exitoso mediante Django auth',
        exitoso=True
    )


@receiver(user_logged_out)
def usuario_logged_out(sender, request, user, **kwargs):
    """Signal que se ejecuta cuando un usuario cierra sesión"""
    if user and user.is_authenticated:
        # Crear registro de log
        LogAcceso.objects.create(
            usuario=user,
            tipo_evento='LOGOUT',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            detalles='Logout mediante Django auth',
            exitoso=True
        )
        
        # Marcar sesiones como inactivas
        SesionUsuario.objects.filter(
            usuario=user,
            activa=True
        ).update(activa=False)


@receiver(user_login_failed)
def usuario_login_failed(sender, credentials, request, **kwargs):
    """Signal que se ejecuta cuando falla un intento de login"""
    email = credentials.get('username') or credentials.get('email')
    
    # Crear registro de log
    LogAcceso.objects.create(
        email_intento=email,
        tipo_evento='LOGIN_FAILED',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        detalles='Login fallido mediante Django auth',
        exitoso=False
    )
    
    # Si existe el usuario, incrementar intentos fallidos
    if email:
        try:
            user = Usuario.objects.get(email=email)
            user.incrementar_intentos_fallidos()
        except Usuario.DoesNotExist:
            pass


# Signal personalizado para cambios de contraseña
from django.contrib.auth import user_logged_in

@receiver(post_save, sender=Usuario)
def detectar_cambio_password(sender, instance, created, **kwargs):
    """Detectar cambios de contraseña"""
    if not created and hasattr(instance, '_password_changed'):
        LogAcceso.objects.create(
            usuario=instance,
            tipo_evento='PASSWORD_CHANGE',
            ip_address='127.0.0.1',
            user_agent='Sistema',
            detalles='Contraseña cambiada',
            exitoso=True
        )
        
        # Cerrar todas las sesiones del usuario
        SesionUsuario.objects.filter(
            usuario=instance,
            activa=True
        ).update(activa=False)


# Signal para limpiar tokens de recuperación expirados
from django.db.models.signals import post_migrate
from django.core.management.base import BaseCommand

@receiver(post_migrate)
def limpiar_tokens_expirados(sender, **kwargs):
    """Limpiar tokens de recuperación expirados"""
    if sender.name == 'apps.authentication':
        try:
            now = timezone.now()
            Usuario.objects.filter(
                fecha_expiracion_token__lt=now
            ).update(
                token_recuperacion='',
                fecha_expiracion_token=None
            )
        except Exception:
            pass  # Ignorar errores durante migraciones


# Signal para limpiar sesiones inactivas
from celery import shared_task

@shared_task
def limpiar_sesiones_inactivas():
    """Tarea para limpiar sesiones inactivas (ejecutar periódicamente)"""
    from datetime import timedelta
    
    # Marcar como inactivas las sesiones que no han tenido actividad en 24 horas
    limite = timezone.now() - timedelta(hours=24)
    SesionUsuario.objects.filter(
        fecha_ultimo_acceso__lt=limite,
        activa=True
    ).update(activa=False)
    
    # Eliminar logs antiguos (opcional, mantener solo últimos 3 meses)
    limite_logs = timezone.now() - timedelta(days=90)
    LogAcceso.objects.filter(fecha_evento__lt=limite_logs).delete()


# Signal para validaciones adicionales de seguridad
@receiver(pre_save, sender=Usuario)
def validaciones_seguridad(sender, instance, **kwargs):
    """Validaciones adicionales de seguridad"""
    # Convertir código de empleado a mayúsculas
    if instance.codigo_empleado:
        instance.codigo_empleado = instance.codigo_empleado.upper()
    
    # Normalizar email
    if instance.email:
        instance.email = instance.email.lower().strip()
    
    # Validar que no se pueda auto-bloquear (en caso de edición directa)
    if instance.pk:
        try:
            original = Usuario.objects.get(pk=instance.pk)
            # Si se está intentando cambiar su propio estado a bloqueado desde admin
            # (esto se maneja mejor en las vistas, pero es una capa adicional)
            if (original.estado != 'BLOQUEADO' and 
                instance.estado == 'BLOQUEADO' and 
                hasattr(instance, '_current_user') and 
                instance._current_user and 
                instance._current_user.id == instance.id):
                instance.estado = original.estado
        except Usuario.DoesNotExist:
            pass