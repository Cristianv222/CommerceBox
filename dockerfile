# CommerceBox - Sistema de Inventario Comercial Dual
# Dockerfile

FROM python:3.11-slim

# Metadatos
LABEL maintainer="CommerceBox Team"
LABEL description="Sistema de Inventario Comercial Dual"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gettext \
        curl \
        wget \
        git \
        nano \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del proyecto
COPY . /app/

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/media /app/static

# Permisos para el script de entrada
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Crear usuario no root
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8000

# Comando por defecto
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]