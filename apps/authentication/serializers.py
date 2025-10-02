from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from .models import Usuario, PermisoPersonalizado, SesionUsuario, LogAcceso
import uuid
from .models import Usuario, PermisoPersonalizado, SesionUsuario, LogAcceso, Rol

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado para obtener tokens JWT"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar claims personalizados al token
        token['user_id'] = str(user.id)
        token['email'] = user.email
        token['full_name'] = user.get_full_name()
        token['rol'] = user.rol
        token['codigo_empleado'] = user.codigo_empleado
        token['is_admin'] = user.is_admin()
        token['is_supervisor'] = user.is_supervisor()
        token['permisos'] = {
            'inventory': user.puede_acceder_modulo('inventory'),
            'sales': user.puede_acceder_modulo('sales'),
            'financial': user.puede_acceder_modulo('financial'),
            'reports': user.puede_acceder_modulo('reports'),
            'notifications': user.puede_acceder_modulo('notifications'),
            'system_config': user.puede_acceder_modulo('system_config'),
        }
        
        return token
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Obtener información de la request
            request = self.context.get('request')
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            try:
                user = Usuario.objects.get(username=username)
                
                # Verificar si el usuario está bloqueado
                if user.esta_bloqueado():
                    # Registrar intento de acceso a cuenta bloqueada
                    LogAcceso.objects.create(
                        usuario=user,
                        email_intento=username,
                        tipo_evento='LOGIN_FAILED',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        detalles='Intento de acceso a cuenta bloqueada',
                        exitoso=False
                    )
                    raise serializers.ValidationError(
                        'Cuenta bloqueada por múltiples intentos fallidos. Contacte al administrador.'
                    )
                
                # Verificar estado del usuario
                if user.estado != 'ACTIVO':
                    LogAcceso.objects.create(
                        usuario=user,
                        email_intento=username,
                        tipo_evento='LOGIN_FAILED',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        detalles=f'Intento de acceso con estado: {user.estado}',
                        exitoso=False
                    )
                    raise serializers.ValidationError(f'Usuario {user.estado.lower()}. Contacte al administrador.')
                
                # Autenticar usuario
                user = authenticate(request=request, username=username, password=password)
                
                if not user:
                    # Usuario existe pero contraseña incorrecta
                    usuario_obj = Usuario.objects.get(username=username)
                    usuario_obj.incrementar_intentos_fallidos()
                    
                    LogAcceso.objects.create(
                        usuario=usuario_obj,
                        email_intento=username,
                        tipo_evento='LOGIN_FAILED',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        detalles='Contraseña incorrecta',
                        exitoso=False
                    )
                    
                    raise serializers.ValidationError('Credenciales inválidas.')
                
                # Login exitoso
                user.reset_intentos_fallidos()
                user.fecha_ultimo_acceso = timezone.now()
                user.save()
                
                # Crear sesión
                token_session = str(uuid.uuid4())
                SesionUsuario.objects.create(
                    usuario=user,
                    token_session=token_session,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Registrar login exitoso
                LogAcceso.objects.create(
                    usuario=user,
                    tipo_evento='LOGIN',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detalles='Login exitoso',
                    exitoso=True
                )
                
            except Usuario.DoesNotExist:
                # Registrar intento con username inexistente
                LogAcceso.objects.create(
                    email_intento=username,
                    tipo_evento='LOGIN_FAILED',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detalles='Username no registrado',
                    exitoso=False
                )
                raise serializers.ValidationError('Credenciales inválidas.')
        
        data = super().validate(attrs)
        return data
    
    def get_client_ip(self, request):
        """Obtener la IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Usuario"""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'codigo_empleado', 'email', 'username', 'nombres', 'apellidos',
            'telefono', 'documento_identidad', 'rol', 'estado', 'is_active',
            'date_joined', 'fecha_ultimo_acceso', 'password', 'confirm_password',
            'full_name', 'intentos_fallidos'
        ]
        read_only_fields = ['id', 'date_joined', 'fecha_ultimo_acceso', 'intentos_fallidos']
    
    def validate(self, attrs):
        if 'password' in attrs and 'confirm_password' in attrs:
            if attrs['password'] != attrs['confirm_password']:
                raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = Usuario.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
            instance.fecha_cambio_password = timezone.now()
        
        instance.save()
        return instance


class UsuarioListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de usuarios"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'codigo_empleado', 'email', 'username', 'full_name',
            'rol', 'rol_display', 'estado', 'estado_display', 'is_active',
            'fecha_ultimo_acceso', 'intentos_fallidos'
        ]


class CambiarPasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña"""
    
    password_actual = serializers.CharField(required=True)
    password_nueva = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['password_nueva'] != attrs['confirm_password']:
            raise serializers.ValidationError("Las contraseñas nuevas no coinciden.")
        return attrs
    
    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value


class RecuperarPasswordSerializer(serializers.Serializer):
    """Serializer para recuperación de contraseña"""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        try:
            Usuario.objects.get(email=value, is_active=True)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("No existe un usuario activo con este email.")
        return value


class RestablecerPasswordSerializer(serializers.Serializer):
    """Serializer para restablecer contraseña con token"""
    
    token = serializers.CharField(required=True)
    password_nueva = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['password_nueva'] != attrs['confirm_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs
    
    def validate_token(self, value):
        try:
            user = Usuario.objects.get(
                token_recuperacion=value,
                fecha_expiracion_token__gt=timezone.now()
            )
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Token inválido o expirado.")
        return value


class PermisoPersonalizadoSerializer(serializers.ModelSerializer):
    """Serializer para permisos personalizados"""
    
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = PermisoPersonalizado
        fields = [
            'id', 'usuario', 'usuario_nombre', 'modulo', 'accion',
            'activo', 'fecha_asignacion', 'fecha_expiracion'
        ]
        read_only_fields = ['fecha_asignacion']


class SesionUsuarioSerializer(serializers.ModelSerializer):
    """Serializer para sesiones de usuario"""
    
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = SesionUsuario
        fields = [
            'id', 'usuario', 'usuario_nombre', 'ip_address', 'user_agent',
            'fecha_inicio', 'fecha_ultimo_acceso', 'activa'
        ]
        read_only_fields = ['fecha_inicio', 'fecha_ultimo_acceso']


class LogAccesoSerializer(serializers.ModelSerializer):
    """Serializer para logs de acceso"""
    
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    tipo_evento_display = serializers.CharField(source='get_tipo_evento_display', read_only=True)
    
    class Meta:
        model = LogAcceso
        fields = [
            'id', 'usuario', 'usuario_nombre', 'email_intento', 'tipo_evento',
            'tipo_evento_display', 'ip_address', 'user_agent', 'detalles',
            'fecha_evento', 'exitoso'
        ]
        read_only_fields = ['fecha_evento']


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    """Serializer para el perfil del usuario autenticado"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'codigo_empleado', 'email', 'username', 'nombres', 'apellidos',
            'telefono', 'documento_identidad', 'rol', 'rol_display', 'full_name',
            'fecha_ultimo_acceso', 'permisos'
        ]
        read_only_fields = ['id', 'codigo_empleado', 'rol', 'fecha_ultimo_acceso']
    
    def get_permisos(self, obj):
        """Obtener permisos del usuario"""
        return {
            'inventory': obj.puede_acceder_modulo('inventory'),
            'sales': obj.puede_acceder_modulo('sales'),
            'financial': obj.puede_acceder_modulo('financial'),
            'reports': obj.puede_acceder_modulo('reports'),
            'notifications': obj.puede_acceder_modulo('notifications'),
            'system_config': obj.puede_acceder_modulo('system_config'),
            'is_admin': obj.is_admin(),
            'is_supervisor': obj.is_supervisor(),
            'is_vendedor': obj.is_vendedor(),
            'is_cajero': obj.is_cajero(),
        }

class RolSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Rol"""
    
    class Meta:
        model = Rol
        fields = [
            'id', 'nombre', 'codigo', 'descripcion', 'permissions',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_codigo(self, value):
        """Validar formato del código"""
        if not value.isupper():
            raise serializers.ValidationError("El código debe estar en mayúsculas")
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("El código solo puede contener letras, números, guiones y guiones bajos")
        return value
    
    def validate_permissions(self, value):
        """Validar que permissions sea una lista"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Los permisos deben ser una lista")
        return value