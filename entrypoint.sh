#!/bin/bash
# CommerceBox - Entrypoint inteligente que maneja migraciones automáticamente

set -e

# Función para logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Iniciando CommerceBox..."

# Esperar a que la base de datos esté disponible
log "Verificando conexión a base de datos..."
while ! pg_isready -h ${COMMERCEBOX_DB_HOST:-commercebox-db} -p ${COMMERCEBOX_DB_PORT:-5432} -U ${COMMERCEBOX_DB_USER:-commercebox_user}; do
    log "Esperando a PostgreSQL..."
    sleep 2
done

log "Base de datos disponible"

# Verificar configuración de Django
log "Verificando configuración de Django..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
import django
django.setup()
from django.conf import settings
print(f'AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}')
print('Configuración verificada')
" || {
    log "ERROR: Problema en configuración de Django"
    exit 1
}

# Función para crear migración inicial de authentication si no existe
# COMENTADO TEMPORALMENTE PARA EVITAR CONFLICTOS CON UUID
# create_auth_migration() {
#     local migrations_dir="apps/authentication/migrations"
#     
#     # Crear directorio migrations si no existe
#     if [ ! -d "$migrations_dir" ]; then
#         log "Creando directorio migrations para authentication..."
#         mkdir -p "$migrations_dir"
#         touch "$migrations_dir/__init__.py"
#     fi
#     
#     # Verificar si ya existe migración inicial
#     if [ ! -f "$migrations_dir/0001_initial.py" ]; then
#         log "Creando migración inicial para authentication..."
#         
#         cat > "$migrations_dir/0001_initial.py" << 'EOF'
# # Generated automatically by entrypoint.sh
# 
# from django.contrib.auth.validators import UnicodeUsernameValidator
# from django.db import migrations, models
# import django.contrib.auth.models
# import django.utils.timezone
# 
# 
# class Migration(migrations.Migration):
# 
#     initial = True
# 
#     dependencies = [
#         ('auth', '0012_alter_user_first_name_max_length'),
#     ]
# 
#     operations = [
#         migrations.CreateModel(
#             name='Usuario',
#             fields=[
#                 ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
#                 ('password', models.CharField(max_length=128, verbose_name='password')),
#                 ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
#                 ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
#                 ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[UnicodeUsernameValidator()], verbose_name='username')),
#                 ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
#                 ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
#                 ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
#                 ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
#                 ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
#                 ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
#                 ('telefono', models.CharField(blank=True, max_length=20, null=True)),
#                 ('cedula', models.CharField(blank=True, max_length=20, null=True, unique=True)),
#                 ('cargo', models.CharField(blank=True, max_length=100, null=True)),
#                 ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
#                 ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
#                 ('activo', models.BooleanField(default=True)),
#                 ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
#                 ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
#             ],
#             options={
#                 'verbose_name': 'Usuario',
#                 'verbose_name_plural': 'Usuarios',
#             },
#             managers=[
#                 ('objects', django.contrib.auth.models.UserManager()),
#             ],
#         ),
#     ]
# EOF
#         
#         log "Migración inicial de authentication creada"
#     else
#         log "Migración de authentication ya existe"
#     fi
# }

# Crear migraciones para todas las apps que las necesiten
log "Verificando y creando migraciones..."

# Crear migración de authentication específicamente
# COMENTADO TEMPORALMENTE
# create_auth_migration

# Intentar crear migraciones adicionales para otras apps
# COMENTADO TEMPORALMENTE
# log "Creando migraciones adicionales..."
# python manage.py makemigrations --noinput || {
#     log "Warning: No se pudieron crear migraciones adicionales (esto es normal si no hay cambios)"
# }

# Mostrar estado de migraciones
# COMENTADO TEMPORALMENTE
# log "Estado actual de migraciones:"
# python manage.py showmigrations || log "No se pudo mostrar el estado de migraciones"

# Ejecutar migraciones
# COMENTADO TEMPORALMENTE - Ejecutar manualmente después de crear migraciones con UUID
# log "Aplicando migraciones..."
# python manage.py migrate --noinput

log "NOTA: Migraciones comentadas temporalmente. Ejecutar manualmente:"
log "  docker-compose exec commercebox-web python manage.py makemigrations"
log "  docker-compose exec commercebox-web python manage.py migrate"

# Recopilar archivos estáticos si está configurado
if python -c "
from django.conf import settings
import os
static_root = getattr(settings, 'STATIC_ROOT', None)
if static_root and static_root != '':
    print('HAS_STATIC_ROOT')
    exit(0)
exit(1)
" 2>/dev/null; then
    log "Recopilando archivos estáticos..."
    python manage.py collectstatic --noinput --clear || log "Warning: collectstatic falló"
else
    log "STATIC_ROOT no configurado, saltando collectstatic"
fi

# Crear superusuario automáticamente
# COMENTADO TEMPORALMENTE - Crear después de ejecutar migraciones
# log "Configurando superusuario..."
# python -c "
# import os
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
# import django
# django.setup()
# 
# from django.contrib.auth import get_user_model
# 
# try:
#     User = get_user_model()
#     if not User.objects.filter(username='admin').exists():
#         User.objects.create_superuser(
#             username='admin',
#             email='admin@commercebox.local',
#             password='admin123',
#             first_name='Administrador',
#             last_name='Sistema'
#         )
#         print('Superusuario admin creado - Password: admin123')
#     else:
#         print('Superusuario admin ya existe')
# except Exception as e:
#     print(f'Error configurando superusuario: {e}')
# "

# Ejecutar comando setup_commercebox si existe
if python manage.py help | grep -q setup_commercebox 2>/dev/null; then
    log "Ejecutando configuración personalizada..."
    python manage.py setup_commercebox || log "Warning: setup_commercebox falló"
else
    log "Comando setup_commercebox no disponible"
fi

# Mostrar resumen final
log "Resumen de configuración:"
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
import django
django.setup()

from django.conf import settings

print(f'DEBUG: {settings.DEBUG}')
print(f'DATABASE: {settings.DATABASES[\"default\"][\"NAME\"]}')
print(f'USER_MODEL: {settings.AUTH_USER_MODEL}')
print('Base de datos lista - Ejecutar migraciones manualmente')
"

log "CommerceBox iniciado correctamente"
log ""
log "==================================================="
log "INSTRUCCIONES PARA COMPLETAR LA CONFIGURACIÓN:"
log "==================================================="
log "1. Crear migraciones:"
log "   docker-compose exec commercebox-web python manage.py makemigrations"
log ""
log "2. Aplicar migraciones:"
log "   docker-compose exec commercebox-web python manage.py migrate"
log ""
log "3. Crear superusuario:"
log "   docker-compose exec commercebox-web python manage.py createsuperuser"
log ""
log "4. Acceder al panel admin: http://localhost:8000/admin/"
log "==================================================="

# Ejecutar el comando solicitado
exec "$@"