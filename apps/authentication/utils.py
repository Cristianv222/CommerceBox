"""
Funciones auxiliares para el módulo de autenticación
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid
import secrets
import string


def generar_codigo_empleado(prefijo='EMP'):
    """
    Genera un código único de empleado
    
    Args:
        prefijo (str): Prefijo para el código (default: 'EMP')
    
    Returns:
        str: Código de empleado único (ej: EMP001)
    """
    from .models import Usuario
    
    # Obtener el último código
    ultimo_usuario = Usuario.objects.filter(
        codigo_empleado__startswith=prefijo
    ).order_by('-codigo_empleado').first()
    
    if ultimo_usuario and ultimo_usuario.codigo_empleado:
        # Extraer número del último código
        try:
            numero = int(ultimo_usuario.codigo_empleado.replace(prefijo, ''))
            nuevo_numero = numero + 1
        except ValueError:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    # Formatear con ceros a la izquierda
    return f"{prefijo}{nuevo_numero:03d}"


def generar_token_seguro(length=32):
    """
    Genera un token aleatorio seguro
    
    Args:
        length (int): Longitud del token
    
    Returns:
        str: Token seguro
    """
    return secrets.token_urlsafe(length)


def generar_password_temporal(length=12):
    """
    Genera una contraseña temporal segura
    
    Args:
        length (int): Longitud de la contraseña
    
    Returns:
        str: Contraseña temporal
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Asegurar que tenga al menos una mayúscula, minúscula, número y símbolo
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.islower() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_lowercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + secrets.choice(string.digits)
    if not any(c in "!@#$%^&*" for c in password):
        password = password[:-1] + secrets.choice("!@#$%^&*")
    
    return password


def enviar_email_bienvenida(usuario, password_temporal=None):
    """
    Envía email de bienvenida a un nuevo usuario
    
    Args:
        usuario: Instancia del usuario
        password_temporal: Contraseña temporal si es necesario
    """
    subject = f'Bienvenido a CommerceBox - {usuario.get_full_name()}'
    
    if password_temporal:
        message = f"""
        Hola {usuario.get_full_name()},
        
        Bienvenido a CommerceBox. Tu cuenta ha sido creada exitosamente.
        
        Credenciales de acceso:
        - Email: {usuario.email}
        - Contraseña temporal: {password_temporal}
        - Rol: {usuario.get_rol_display()}
        
        Por seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.
        
        Puedes acceder al sistema en: {settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}
        
        Saludos,
        Equipo CommerceBox
        """
    else:
        message = f"""
        Hola {usuario.get_full_name()},
        
        Bienvenido a CommerceBox. Tu cuenta ha sido creada exitosamente.
        
        Email de acceso: {usuario.email}
        Rol: {usuario.get_rol_display()}
        
        Saludos,
        Equipo CommerceBox
        """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [usuario.email],
        fail_silently=False,
    )


def enviar_notificacion_bloqueo(usuario):
    """
    Envía notificación cuando un usuario es bloqueado
    
    Args:
        usuario: Instancia del usuario bloqueado
    """
    subject = 'Cuenta bloqueada - CommerceBox'
    
    message = f"""
    Hola {usuario.get_full_name()},
    
    Tu cuenta en CommerceBox ha sido bloqueada debido a múltiples intentos fallidos de inicio de sesión.
    
    Por seguridad, tu cuenta quedará bloqueada por 24 horas.
    
    Si no reconoces esta actividad, contacta inmediatamente al administrador del sistema.
    
    Saludos,
    Equipo CommerceBox
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [usuario.email],
        fail_silently=True,  # No interrumpir el proceso si falla el email
    )


def validar_fuerza_password(password):
    """
    Valida la fuerza de una contraseña
    
    Args:
        password (str): Contraseña a validar
    
    Returns:
        tuple: (es_valida, mensaje_error)
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not any(c.isupper() for c in password):
        return False, "La contraseña debe contener al menos una mayúscula"
    
    if not any(c.islower() for c in password):
        return False, "La contraseña debe contener al menos una minúscula"
    
    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe contener al menos un número"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "La contraseña debe contener al menos un carácter especial"
    
    return True, ""


def obtener_resumen_usuario(usuario):
    """
    Obtiene un resumen completo de un usuario
    
    Args:
        usuario: Instancia del usuario
    
    Returns:
        dict: Diccionario con información del usuario
    """
    from .models import LogAcceso, SesionUsuario
    
    # Obtener últimos accesos
    ultimos_accesos = LogAcceso.objects.filter(
        usuario=usuario,
        tipo_evento='LOGIN',
        exitoso=True
    ).order_by('-fecha_evento')[:5]
    
    # Sesiones activas
    sesiones_activas = SesionUsuario.objects.filter(
        usuario=usuario,
        activa=True
    ).count()
    
    # Intentos fallidos recientes (últimas 24h)
    hace_24h = timezone.now() - timedelta(hours=24)
    intentos_fallidos_24h = LogAcceso.objects.filter(
        usuario=usuario,
        tipo_evento='LOGIN_FAILED',
        fecha_evento__gte=hace_24h
    ).count()
    
    return {
        'id': str(usuario.id),
        'email': usuario.email,
        'full_name': usuario.get_full_name(),
        'codigo_empleado': usuario.codigo_empleado,
        'rol': usuario.rol,
        'rol_display': usuario.get_rol_display(),
        'estado': usuario.estado,
        'estado_display': usuario.get_estado_display(),
        'fecha_creacion': usuario.date_joined,
        'fecha_ultimo_acceso': usuario.fecha_ultimo_acceso,
        'intentos_fallidos': usuario.intentos_fallidos,
        'esta_bloqueado': usuario.esta_bloqueado(),
        'sesiones_activas': sesiones_activas,
        'intentos_fallidos_24h': intentos_fallidos_24h,
        'ultimos_accesos': [
            {
                'fecha': acceso.fecha_evento,
                'ip': acceso.ip_address
            } for acceso in ultimos_accesos
        ],
        'permisos': {
            'is_admin': usuario.is_admin(),
            'is_supervisor': usuario.is_supervisor(),
            'is_vendedor': usuario.is_vendedor(),
            'is_cajero': usuario.is_cajero(),
        }
    }


def limpiar_sesiones_expiradas(usuario=None):
    """
    Limpia sesiones expiradas (>24 horas sin actividad)
    
    Args:
        usuario: Si se especifica, solo limpia sesiones de ese usuario
    
    Returns:
        int: Número de sesiones limpiadas
    """
    from .models import SesionUsuario
    
    limite = timezone.now() - timedelta(hours=24)
    
    query = SesionUsuario.objects.filter(
        fecha_ultimo_acceso__lt=limite,
        activa=True
    )
    
    if usuario:
        query = query.filter(usuario=usuario)
    
    count = query.update(activa=False)
    
    return count


def obtener_estadisticas_seguridad(dias=7):
    """
    Obtiene estadísticas de seguridad del sistema
    
    Args:
        dias (int): Número de días a considerar
    
    Returns:
        dict: Estadísticas de seguridad
    """
    from .models import Usuario, LogAcceso, SesionUsuario
    from django.db.models import Count
    
    fecha_inicio = timezone.now() - timedelta(days=dias)
    
    stats = {
        'periodo_dias': dias,
        'usuarios_totales': Usuario.objects.count(),
        'usuarios_activos': Usuario.objects.filter(
            is_active=True,
            estado='ACTIVO'
        ).count(),
        'usuarios_bloqueados': Usuario.objects.filter(
            estado='BLOQUEADO'
        ).count(),
        'sesiones_activas': SesionUsuario.objects.filter(activa=True).count(),
        'logins_exitosos': LogAcceso.objects.filter(
            tipo_evento='LOGIN',
            exitoso=True,
            fecha_evento__gte=fecha_inicio
        ).count(),
        'logins_fallidos': LogAcceso.objects.filter(
            tipo_evento='LOGIN_FAILED',
            fecha_evento__gte=fecha_inicio
        ).count(),
        'cambios_password': LogAcceso.objects.filter(
            tipo_evento='PASSWORD_CHANGE',
            fecha_evento__gte=fecha_inicio
        ).count(),
        'accesos_denegados': LogAcceso.objects.filter(
            tipo_evento='PERMISSION_DENIED',
            fecha_evento__gte=fecha_inicio
        ).count(),
        'top_ips_fallidos': list(
            LogAcceso.objects.filter(
                tipo_evento='LOGIN_FAILED',
                fecha_evento__gte=fecha_inicio
            ).values('ip_address').annotate(
                total=Count('id')
            ).order_by('-total')[:10]
        ),
        'usuarios_por_rol': list(
            Usuario.objects.values('rol').annotate(
                total=Count('id')
            ).order_by('rol')
        )
    }
    
    return stats


def es_password_comprometida(password):
    """
    Verifica si una contraseña está en la lista de contraseñas comunes
    
    Args:
        password (str): Contraseña a verificar
    
    Returns:
        bool: True si está comprometida
    """
    # Lista de las 100 contraseñas más comunes
    passwords_comunes = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'monkey', '1234567', 'letmein', 'trustno1', 'dragon',
        'baseball', '111111', 'iloveyou', 'master', 'sunshine',
        'ashley', 'bailey', 'passw0rd', 'shadow', '123123',
        '654321', 'superman', 'qazwsx', 'michael', 'football',
        # ... agregar más según necesidad
    ]
    
    return password.lower() in passwords_comunes


def formatear_tiempo_desde(fecha):
    """
    Formatea el tiempo transcurrido desde una fecha
    
    Args:
        fecha: Fecha a formatear
    
    Returns:
        str: Texto formateado (ej: "hace 2 horas")
    """
    if not fecha:
        return "Nunca"
    
    ahora = timezone.now()
    diferencia = ahora - fecha
    
    segundos = diferencia.total_seconds()
    
    if segundos < 60:
        return "hace menos de un minuto"
    elif segundos < 3600:
        minutos = int(segundos / 60)
        return f"hace {minutos} minuto{'s' if minutos != 1 else ''}"
    elif segundos < 86400:
        horas = int(segundos / 3600)
        return f"hace {horas} hora{'s' if horas != 1 else ''}"
    elif segundos < 604800:
        dias = int(segundos / 86400)
        return f"hace {dias} día{'s' if dias != 1 else ''}"
    else:
        return fecha.strftime("%d/%m/%Y")


def validar_email_corporativo(email, dominios_permitidos=None):
    """
    Valida si un email es corporativo
    
    Args:
        email (str): Email a validar
        dominios_permitidos (list): Lista de dominios permitidos
    
    Returns:
        bool: True si es válido
    """
    if not dominios_permitidos:
        dominios_permitidos = getattr(
            settings, 
            'ALLOWED_EMAIL_DOMAINS', 
            ['commercebox.com']
        )
    
    dominio = email.split('@')[-1].lower()
    
    return dominio in dominios_permitidos