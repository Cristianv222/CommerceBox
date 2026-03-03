#!/bin/bash
# ==============================================
# CommerceBox - Entrypoint Optimizado Producción
# ==============================================

set -e  # Detener en cualquier error
set -u  # Error si usa variable no definida
set -o pipefail  # Error en pipes

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de log
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner de inicio
echo ""
echo "=========================================="
echo "🚀 CommerceBox - Sistema de Inventario"
echo "   FronteraTech © 2025"
echo "=========================================="
echo ""

# Variables con valores por defecto
DB_HOST="${COMMERCEBOX_DB_HOST:-commercebox-db}"
DB_PORT="${COMMERCEBOX_DB_PORT:-5432}"
DB_USER="${COMMERCEBOX_DB_USER:-commercebox_user}"
DB_NAME="${COMMERCEBOX_DB_NAME:-commercebox}"
REDIS_HOST="${COMMERCEBOX_REDIS_HOST:-commercebox-redis}"
REDIS_PORT="${COMMERCEBOX_REDIS_PORT:-6379}"
MAX_RETRIES=30
RETRY_INTERVAL=2

# ==============================================
# Función: Esperar PostgreSQL
# ==============================================
wait_for_postgres() {
    log_info "Esperando conexión con PostgreSQL en ${DB_HOST}:${DB_PORT}..."
    
    local retries=0
    until PGPASSWORD="${COMMERCEBOX_DB_PASSWORD}" pg_isready \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        -q > /dev/null 2>&1; do
        
        retries=$((retries + 1))
        
        if [ $retries -ge $MAX_RETRIES ]; then
            log_error "PostgreSQL no disponible después de ${MAX_RETRIES} intentos"
            exit 1
        fi
        
        log_warning "PostgreSQL no disponible, reintentando... (${retries}/${MAX_RETRIES})"
        sleep $RETRY_INTERVAL
    done
    
    log_success "PostgreSQL conectado exitosamente"
}

# ==============================================
# Función: Esperar Redis (solo para servicio web)
# ==============================================
wait_for_redis() {
    log_info "Verificando conexión con Redis en ${REDIS_HOST}:${REDIS_PORT}..."
    
    local retries=0
    until timeout 2 bash -c "echo > /dev/tcp/${REDIS_HOST}/${REDIS_PORT}" 2>/dev/null; do
        retries=$((retries + 1))
        
        if [ $retries -ge $MAX_RETRIES ]; then
            log_error "Redis no disponible después de ${MAX_RETRIES} intentos"
            exit 1
        fi
        
        log_warning "Redis no disponible, reintentando... (${retries}/${MAX_RETRIES})"
        sleep $RETRY_INTERVAL
    done
    
    log_success "Redis conectado exitosamente"
}

# ==============================================
# Función: Ejecutar migraciones
# ==============================================
run_migrations() {
    log_info "Ejecutando migraciones de base de datos..."
    
    if python manage.py migrate --noinput 2>&1 | tee /tmp/migrate.log; then
        log_success "Migraciones aplicadas correctamente"
    else
        log_error "Error al ejecutar migraciones"
        cat /tmp/migrate.log
        exit 1
    fi
}

# ==============================================
# Función: Recolectar archivos estáticos
# ==============================================
collect_static() {
    log_info "Recolectando archivos estáticos..."
    
    if python manage.py collectstatic --noinput --clear 2>&1 | tee /tmp/collectstatic.log; then
        log_success "Archivos estáticos recolectados"
    else
        log_warning "Error al recolectar estáticos (puede ser normal en desarrollo)"
        return 0
    fi
}

# ==============================================
# Función: Limpiar sesiones expiradas
# ==============================================
clean_sessions() {
    log_info "Limpiando sesiones expiradas..."
    
    if python manage.py clearsessions 2>/dev/null; then
        log_success "Sesiones limpias"
    else
        log_warning "No se pudieron limpiar sesiones (continuando...)"
    fi
}

# ==============================================
# Función: Crear usuario inicial de sistema
# ==============================================
create_initial_user() {
    log_info "Verificando usuario inicial del sistema..."
    
    # IMPORTANTE: Estas credenciales son TEMPORALES
    # DEBES cambiarlas inmediatamente después del primer login
    
    python manage.py shell << 'PYTHON_EOF'
import os
import secrets
import string
from django.contrib.auth import get_user_model

def generate_secure_password(length=16):
    """Genera contraseña segura aleatoria"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

User = get_user_model()

# Credenciales del usuario inicial
USERNAME = os.getenv('INITIAL_ADMIN_USERNAME', 'sysoperator')
EMAIL = os.getenv('INITIAL_ADMIN_EMAIL', 'operaciones@agrofacil.fronteratech.ec')

# Contraseña desde variable de entorno o generar una segura
if os.getenv('INITIAL_ADMIN_PASSWORD'):
    PASSWORD = os.getenv('INITIAL_ADMIN_PASSWORD')
else:
    # Generar contraseña temporal segura
    PASSWORD = generate_secure_password(20)

# Verificar si ya existe
if User.objects.filter(username=USERNAME).exists():
    print(f"✓ Usuario del sistema '{USERNAME}' ya existe")
else:
    try:
        user = User.objects.create_superuser(
            username=USERNAME,
            email=EMAIL,
            password=PASSWORD
        )
        
        print("=" * 60)
        print("🔐 CREDENCIALES INICIALES DEL SISTEMA")
        print("=" * 60)
        print(f"Usuario    : {USERNAME}")
        print(f"Email      : {EMAIL}")
        print(f"Contraseña : {PASSWORD}")
        print("=" * 60)
        print("⚠️  IMPORTANTE: Cambia estas credenciales INMEDIATAMENTE")
        print("    después del primer acceso al sistema")
        print("=" * 60)
        
        # Guardar en archivo de logs de forma segura
        log_file = '/app/logs/initial_credentials.txt'
        try:
            with open(log_file, 'w') as f:
                f.write("CREDENCIALES INICIALES - CAMBIAR INMEDIATAMENTE\n")
                f.write("=" * 60 + "\n")
                f.write(f"Usuario    : {USERNAME}\n")
                f.write(f"Email      : {EMAIL}\n")
                f.write(f"Contraseña : {PASSWORD}\n")
                f.write("=" * 60 + "\n")
            
            # Asegurar permisos restrictivos
            os.chmod(log_file, 0o600)
            print(f"📄 Credenciales guardadas en: {log_file}")
            
        except Exception as e:
            print(f"⚠️  No se pudo guardar archivo de credenciales: {e}")
        
    except Exception as e:
        print(f"❌ Error al crear usuario inicial: {e}")
        raise

PYTHON_EOF

    if [ $? -eq 0 ]; then
        log_success "Usuario inicial verificado"
    else
        log_error "Error al crear usuario inicial"
        exit 1
    fi
}

# ==============================================
# Función: Verificar configuración de Django
# ==============================================
check_django_config() {
    log_info "Verificando configuración de Django..."
    
    if python manage.py check --deploy 2>&1 | tee /tmp/django_check.log; then
        log_success "Configuración de Django validada"
    else
        log_warning "Advertencias en configuración de Django:"
        cat /tmp/django_check.log
    fi
}

# ==============================================
# Función: Crear directorios necesarios
# ==============================================
ensure_directories() {
    log_info "Verificando directorios necesarios..."
    
    local dirs=(
        "/app/logs"
        "/app/media"
        "/app/media/uploads"
        "/app/media/invoices"
        "/app/media/reports"
        "/app/staticfiles"
        "/app/backups"
        "/app/tmp"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Creado: $dir"
        fi
    done
    
    log_success "Directorios verificados"
}

# ==============================================
# MAIN: Flujo principal
# ==============================================

# Determinar tipo de servicio
SERVICE_TYPE="${1:-unknown}"

case "$SERVICE_TYPE" in
    gunicorn|python)
        log_info "Modo: Aplicación Web Django / Desarrollo"
        
        # Crear directorios
        ensure_directories
        
        # Esperar servicios
        wait_for_postgres
        wait_for_redis
        
        # Ejecutar migraciones
        run_migrations
        
        # Collectstatic (opcional en desarrollo, pero útil para verificar)
        if [ "$SERVICE_TYPE" = "gunicorn" ]; then
            collect_static
        else
            log_info "Saltando collectstatic en modo desarrollo"
        fi
        
        # Limpiar sesiones
        clean_sessions
        
        # Crear usuario inicial
        create_initial_user
        
        # Verificar configuración (solo en prod)
        if [ "$SERVICE_TYPE" = "gunicorn" ]; then
            check_django_config
        fi
        
        log_success "Aplicación lista para iniciar"
        ;;
        
    celery)
        log_info "Modo: Celery Worker"
        
        # Solo esperar servicios
        wait_for_postgres
        wait_for_redis
        
        log_success "Celery worker listo para iniciar"
        ;;
        
    *)
        log_info "Modo: $SERVICE_TYPE"
        
        # Esperar solo PostgreSQL para otros servicios
        wait_for_postgres
        
        log_success "Servicio listo para iniciar"
        ;;
esac

# ==============================================
# Ejecutar comando principal
# ==============================================
echo ""
echo "=========================================="
log_info "Ejecutando comando: $*"
echo "=========================================="
echo ""

# Ejecutar y reemplazar el proceso actual
exec "$@"