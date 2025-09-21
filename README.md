# CommerceBox 📦
## Sistema de Inventario Comercial Dual

[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**CommerceBox** es un sistema integral de inventario comercial que maneja de forma unificada dos tipos de productos:
- **Quintales a granel** con trazabilidad individual
- **Productos normales** con stock tradicional

## 🎯 **Características Principales**

### 📦 **Inventario Dual Inteligente**
- ✅ **Quintales con trazabilidad FIFO** - Cada quintal tiene código único y seguimiento completo
- ✅ **Productos tradicionales categorizados** - Stock por unidades con control de marcas
- ✅ **Búsqueda unificada** - Un solo campo identifica automáticamente el tipo de producto
- ✅ **Códigos de barras duales** - CBX-QNT para quintales, CBX-PRD para productos

### 💰 **Sistema de Ventas Avanzado**
- ✅ **POS unificado** - Procesa ventas mixtas (quintales + productos) en una factura
- ✅ **Cálculo automático de precios** - Márgenes por categoría aplicados automáticamente
- ✅ **Facturación electrónica** - API integrada compatible con sistemas locales
- ✅ **Múltiples formas de pago** - Efectivo, tarjeta, transferencia, crédito

### 🏦 **Gestión Financiera Dual**
- ✅ **Caja principal** - Manejo de ventas con desglose por tipo de inventario
- ✅ **Caja chica** - Gastos menores categorizados con autorización
- ✅ **Contabilidad automática** - Asientos generados por cada transacción
- ✅ **Conciliación inteligente** - Validación automática entre ventas y efectivo

### 📊 **Reportes y Analytics**
- ✅ **Dashboard en tiempo real** - Métricas duales y KPIs ejecutivos
- ✅ **Trazabilidad completa** - Seguimiento desde origen hasta venta final
- ✅ **Reportes por categoría** - Análisis de rentabilidad diferenciado
- ✅ **Alertas inteligentes** - Stock bajo/crítico automático

## 🚀 **Instalación Rápida**

### **Opción 1: Docker (Recomendada)**

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/commercebox.git
cd commercebox

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 3. Iniciar con Docker
docker-compose up -d

# 4. Acceder a la aplicación
# http://localhost:8000
# Usuario: admin / Contraseña: admin123
```

### **Opción 2: Instalación Local**

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/commercebox.git
cd commercebox

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar base de datos PostgreSQL
createdb commercebox
createuser commercebox_user

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 6. Ejecutar migraciones
python manage.py migrate

# 7. Configurar CommerceBox
python manage.py setup_commercebox

# 8. Iniciar servidor
python manage.py runserver
```

## 📁 **Estructura del Proyecto**

```
COMMERCEBOX/
├── apps/                           # Aplicaciones Django
│   ├── authentication/            # Sistema de usuarios y roles
│   ├── inventory_management/       # Inventario dual (quintales + productos)
│   ├── sales_management/          # POS y ventas unificadas
│   ├── financial_management/      # Caja dual y contabilidad
│   ├── reports_analytics/         # Reportes y dashboard
│   ├── hardware_integration/      # Impresoras, escáneres, básculas
│   ├── notifications/            # Alertas y notificaciones
│   ├── system_configuration/     # Configuración del sistema
│   ├── custom_admin/            # Panel administrativo personalizado
│   └── stock_alert_system/      # Sistema de semáforos de stock
├── commercebox/                 # Configuración Django
├── templates/                   # Plantillas HTML
├── static/                     # Archivos estáticos (CSS, JS, imágenes)
├── media/                      # Archivos subidos (códigos de barras, facturas)
├── docker-compose.yml          # Configuración Docker
└── requirements.txt           # Dependencias Python
```

## 🔧 **Configuración**

### **Variables de Entorno Principales**

```bash
# Django
COMMERCEBOX_SECRET_KEY=tu-clave-secreta
COMMERCEBOX_DEBUG=False
COMMERCEBOX_ALLOWED_HOSTS=tu-dominio.com

# Base de datos
COMMERCEBOX_DB_NAME=commercebox
COMMERCEBOX_DB_USER=commercebox_user
COMMERCEBOX_DB_PASSWORD=tu-contraseña
COMMERCEBOX_DB_HOST=localhost

# Features
COMMERCEBOX_FE_ENABLED=True           # Facturación electrónica
COMMERCEBOX_BACKUP_ENABLED=True       # Backups automáticos
COMMERCEBOX_ALERTAS_ENABLED=True      # Alertas de stock
```

## 🎮 **Uso del Sistema**

### **1. Configuración Inicial**

```bash
# Ejecutar configuración inicial (una sola vez)
python manage.py setup_commercebox

# Crear categorías personalizadas
python manage.py shell
>>> from apps.inventory_management.models import Categoria
>>> Categoria.objects.create(codigo='CAR', nombre='Carnes', margen_ganancia=35.0)
```

### **2. Gestión de Inventario**

```python
# Registrar quintal con trazabilidad
from apps.inventory_management.models import Quintal

quintal = Quintal.objects.create(
    codigo_unico='ARR001',
    nombre='Arroz Premium',
    peso_inicial=100.0,
    peso_actual=100.0,
    precio_por_unidad=2.50,
    proveedor_id=1,
    fecha_ingreso=timezone.now()
)
# Genera automáticamente: codigo_barras = 'CBX-QNT-ARR001'

# Registrar producto normal
from apps.inventory_management.models import ProductoNormal

producto = ProductoNormal.objects.create(
    nombre='Aceite Vegetal 1L',
    categoria_id=1,
    marca_id=1,
    proveedor_id=1,
    stock_actual=50,
    precio_compra=3.00
)
# Calcula automáticamente precio_venta basado en margen de categoría
```

### **3. Ventas Mixtas en POS**

```python
# Procesar venta que combina quintales y productos
from apps.sales_management.services import POSService

items_carrito = [
    {'codigo_barras': 'CBX-QNT-ARR001', 'cantidad': 2.5},  # 2.5kg de arroz
    {'codigo_barras': 'CBX-PRD-ALM-GEN-123', 'cantidad': 3}  # 3 aceites
]

venta = POSService.procesar_venta_mixta(
    items_carrito=items_carrito,
    vendedor=request.user
)
# Resultado: Factura unificada con trazabilidad de quintal
```

## 📊 **API REST**

### **Endpoints Principales**

```bash
# Búsqueda unificada de productos
GET /api/v1/inventory/buscar-producto/?codigo=CBX-QNT-ARR001

# Procesar venta
POST /api/v1/sales/procesar-venta/
{
  "items": [
    {"codigo_barras": "CBX-QNT-ARR001", "cantidad": 2.5},
    {"codigo_barras": "CBX-PRD-ALM-GEN-123", "cantidad": 3}
  ]
}

# Dashboard en tiempo real
GET /api/v1/reports/dashboard/

# Alertas de stock
GET /api/v1/inventory/stock-alerts/
```

## 🔐 **Seguridad**

- ✅ **Autenticación robusta** con tokens y sesiones
- ✅ **Control de acceso por roles** (Admin, Supervisor, Vendedor, Cajero)
- ✅ **Auditoría completa** con logs inmutables
- ✅ **Encriptación de contraseñas** con Django auth
- ✅ **Protección CSRF** y headers de seguridad

## 🧪 **Testing**

```bash
# Ejecutar todas las pruebas
python manage.py test

# Pruebas con cobertura
coverage run manage.py test
coverage report
coverage html

# Pruebas específicas
python manage.py test apps.inventory_management.tests.test_models
python manage.py test apps.sales_management.tests.test_pos
```

## 📋 **Comandos Útiles**

```bash
# Configuración inicial
python manage.py setup_commercebox

# Generar códigos de barras masivos
python manage.py generate_barcodes

# Backup de base de datos
python manage.py backup_system

# Validar integridad de inventario
python manage.py validate_inventory_integrity

# Recalcular semáforos de stock
python manage.py recalcular_stock

# Procesar alertas pendientes
python manage.py procesar_alertas
```

## 🛠️ **Desarrollo**

### **Contribuir al Proyecto**

```bash
# 1. Fork del repositorio
# 2. Crear rama para feature
git checkout -b feature/nueva-funcionalidad

# 3. Hacer cambios y commit
git commit -m "Agregar nueva funcionalidad X"

# 4. Push y crear Pull Request
git push origin feature/nueva-funcionalidad
```

### **Agregar Nueva App**

```bash
# 1. Crear nueva app
python manage.py startapp nueva_app apps/nueva_app

# 2. Agregar a INSTALLED_APPS en settings.py
COMMERCEBOX_APPS = [
    # ... apps existentes
    'apps.nueva_app',
]

# 3. Seguir estructura estándar
apps/nueva_app/
├── models.py
├── views.py
├── urls.py
├── admin.py
├── tests.py
└── services/
```

## 📞 **Soporte y Documentación**

- 📖 **Documentación completa**: [docs/](docs/)
- 🐛 **Reportar bugs**: [Issues](https://github.com/tu-usuario/commercebox/issues)
- 💬 **Discusiones**: [Discussions](https://github.com/tu-usuario/commercebox/discussions)
- 📧 **Email**: soporte@commercebox.com

## 📄 **Licencia**

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🎉 **Créditos**

Desarrollado con ❤️ por el equipo de CommerceBox

- **Framework**: Django 4.2
- **Base de datos**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery
- **Frontend**: Bootstrap + jQuery
- **Containerización**: Docker

---

**CommerceBox** - *La solución definitiva para inventario comercial dual* 📦🚀