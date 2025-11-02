#!/bin/bash
# CommerceBox - Entrypoint para producción

set -e

echo "=========================================="
echo "Iniciando CommerceBox..."
echo "=========================================="

# Esperar a que PostgreSQL esté disponible
echo "Esperando a PostgreSQL..."
while ! pg_isready -h ${COMMERCEBOX_DB_HOST:-commercebox-db} -p ${COMMERCEBOX_DB_PORT:-5432} -U ${COMMERCEBOX_DB_USER:-commercebox_user} > /dev/null 2>&1; do
    sleep 1
done
echo "✓ PostgreSQL disponible"

# Ejecutar migraciones
echo "Ejecutando migraciones..."
python manage.py migrate --noinput
echo "✓ Migraciones aplicadas"

# Recopilar archivos estáticos (CRÍTICO para admin con estilos)
echo "Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear
echo "✓ Archivos estáticos recopilados"

# Crear superusuario por defecto si no existe
echo "Verificando superusuario..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@agrototal.com',
        password='Admin123!',
        first_name='Administrador',
        last_name='Sistema'
    )
    print('✓ Superusuario creado: admin / Admin123!')
else:
    print('✓ Superusuario ya existe')
EOF

echo "=========================================="
echo "CommerceBox listo"
echo "=========================================="
echo ""

# Ejecutar comando (Gunicorn)
exec "$@"
```
