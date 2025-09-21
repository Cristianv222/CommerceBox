#!/bin/bash
# CommerceBox - Script de entrada para Docker

set -e

# Función para logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "🚀 Iniciando CommerceBox..."

# Esperar a que la base de datos esté disponible
log "📡 Verificando conexión a base de datos..."
while ! pg_isready -h ${COMMERCEBOX_DB_HOST:-localhost} -p ${COMMERCEBOX_DB_PORT:-5432} -U ${COMMERCEBOX_DB_USER:-commercebox_user}; do
    log "⏳ Esperando a PostgreSQL..."
    sleep 2
done

log "✅ Base de datos disponible"

# Ejecutar migraciones
log "🔄 Ejecutando migraciones..."
python manage.py migrate --noinput

# Recopilar archivos estáticos
log "📦 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Crear superusuario si no existe
log "👤 Verificando superusuario..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@commercebox.com', 'admin123')
    print("Superusuario 'admin' creado")
else:
    print("Superusuario ya existe")
EOF

# Configurar CommerceBox si es la primera vez
log "⚙️ Configurando CommerceBox..."
python manage.py setup_commercebox || log "⚠️ Configuración ya existe o falló"

# Cargar datos iniciales si existen
if [ -f "fixtures/initial_data.json" ]; then
    log "📋 Cargando datos iniciales..."
    python manage.py loaddata fixtures/initial_data.json
fi

log "🎉 CommerceBox iniciado correctamente"

# Ejecutar comando
exec "$@"