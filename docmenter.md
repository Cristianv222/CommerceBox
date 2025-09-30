COMMERCEBOX/
├── 📄 .gitignore
├── 📄 create_structure.ps1
├── ⚙️ docker-compose.yml
├── 📄 dockerfile
├── 🐍 documenter.py
├── 📄 entrypoint.sh
├── 🐍 manage.py
├── 📄 requirements.txt
├── 📁 apps/
│   ├── 🐍 __init__.py
│   ├── 🐍 context_processors.py
│   │
│   ├── 📁 authentication/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 forms.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 urls.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 management/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 📁 commands/
│   │   │       ├── 🐍 __init__.py
│   │   └── 📁 migrations/
│   │       ├── 🐍 0001_initial.py
│   │       └── 🐍 __init__.py
│   │
│   ├── 📁 inventory_management/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 forms.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 signals.py
│   │   ├── 🐍 tasks.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 urls.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 management/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 📁 commands/
│   │   │       ├── 🐍 __init__.py
│   │   │       ├── 🐍 setup_inventory_data.py
│   │   │       ├── 🐍 validate_inventory_integrity.py
│   │   │       └── 🐍 generate_barcodes.py
│   │   ├── 📁 migrations/
│   │   │   ├── 🐍 0001_initial.py
│   │   │   └── 🐍 __init__.py
│   │   ├── 📁 services/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 inventory_service.py
│   │   │   ├── 🐍 traceability_service.py
│   │   │   ├── 🐍 stock_service.py
│   │   │   └── 🐍 barcode_service.py
│   │   └── 📁 utils/
│   │       ├── 🐍 __init__.py
│   │       ├── 🐍 barcode_generator.py
│   │       ├── 🐍 unit_converter.py
│   │       ├── 🐍 validators.py
│   │       └── 🐍 fifo_calculator.py
│   │
│   ├── 📁 sales_management/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 forms.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 signals.py
│   │   ├── 🐍 tasks.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 urls.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 pos/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 pos_service.py
│   │   │   ├── 🐍 pricing_calculator.py
│   │   │   └── 🐍 discount_manager.py
│   │   ├── 📁 invoicing/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 invoice_service.py
│   │   │   ├── 🐍 electronic_invoice.py
│   │   │   └── 🐍 ticket_generator.py
│   │   └── 📁 migrations/
│   │       ├── 🐍 0001_initial.py
│   │       └── 🐍 __init__.py
│   │
│   ├── 📁 financial_management/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 forms.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 signals.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 urls.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 migrations/
│   │   │   ├── 🐍 0001_initial.py
│   │   │   └── 🐍 __init__.py
│   │   ├── 📁 cash_management/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 cash_service.py
│   │   │   ├── 🐍 reconciliation_service.py
│   │   │   └── 🐍 cash_calculator.py
│   │   └── 📁 accounting/
│   │       ├── 🐍 __init__.py
│   │       ├── 🐍 accounting_service.py
│   │       ├── 🐍 entry_generator.py
│   │       └── 🐍 cost_calculator.py
│   │
│   ├── 📁 reports_analytics/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 forms.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 urls.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 generators/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 dashboard_data.py
│   │   │   ├── 🐍 inventory_reports.py
│   │   │   ├── 🐍 sales_reports.py
│   │   │   ├── 🐍 financial_reports.py
│   │   │   └── 🐍 traceability_reports.py
│   │   └── 📁 migrations/
│   │       ├── 🐍 0001_initial.py
│   │       └── 🐍 __init__.py
│   │
│   ├── 📁 hardware_integration/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 printers/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 thermal_printer.py
│   │   │   ├── 🐍 label_printer.py
│   │   │   └── 🐍 escpos_formatter.py
│   │   ├── 📁 scanners/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 barcode_scanner.py
│   │   │   └── 🐍 scanner_service.py
│   │   ├── 📁 scales/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 electronic_scale.py
│   │   │   └── 🐍 weight_service.py
│   │   └── 📁 cash_drawer/
│   │       ├── 🐍 __init__.py
│   │       └── 🐍 drawer_controller.py
│   │
│   ├── 📁 notifications/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 migrations/
│   │   │   ├── 🐍 0001_initial.py
│   │   │   └── 🐍 __init__.py
│   │   └── 📁 services/
│   │       ├── 🐍 __init__.py
│   │       ├── 🐍 stock_alerts.py
│   │       ├── 🐍 notification_service.py
│   │       └── 🐍 alert_generator.py
│   │
│   ├── 📁 system_configuration/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 admin.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 models.py
│   │   ├── 🐍 tests.py
│   │   ├── 🐍 views.py
│   │   ├── 📁 management/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 📁 commands/
│   │   │       ├── 🐍 __init__.py
│   │   │       ├── 🐍 backup_system.py
│   │   │       ├── 🐍 setup_initial_data.py
│   │   │       └── 🐍 system_health_check.py
│   │   └── 📁 migrations/
│   │       ├── 🐍 0001_initial.py
│   │       └── 🐍 __init__.py
│   │
│   ├── 📁 custom_admin/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 apps.py
│   │   ├── 🐍 urls.py
│   │   └── 🐍 views.py
│   │
│   └── 📁 stock_alert_system/
│       ├── 🐍 __init__.py
│       ├── 🐍 admin.py
│       ├── 🐍 apps.py
│       ├── 🐍 forms.py
│       ├── 🐍 models.py
│       ├── 🐍 signals.py
│       ├── 🐍 status_calculator.py
│       ├── 🐍 tests.py
│       ├── 🐍 urls.py
│       ├── 🐍 views.py
│       ├── 📁 management/
│       │   ├── 🐍 __init__.py
│       │   └── 📁 commands/
│       │       ├── 🐍 __init__.py
│       │       ├── 🐍 procesar_alertas.py
│       │       └── 🐍 recalcular_stock.py
│       ├── 📁 migrations/
│       │   ├── 🐍 0001_initial.py
│       │   └── 🐍 __init__.py
│       └── 📁 utils/
│           ├── 🐍 __init__.py
│           └── 🐍 stock_calculator.py
│
├── 📁 commercebox/
│   ├── 🐍 __init__.py
│   ├── 🐍 asgi.py
│   ├── 🐍 settings.py
│   ├── 🐍 urls.py
│   └── 🐍 wsgi.py
│
├── 📁 static/
│   ├── 📋 manifest.json
│   ├── 📜 sw.js
│   ├── 📁 icons/
│   │   ├── 🖼️ favicon-16x16.png
│   │   ├── 🖼️ favicon-32x32.png
│   │   ├── 🖼️ favicon-48x48.png
│   │   ├── 📄 favicon.ico
│   │   ├── 🖼️ icon-128x128.png
│   │   ├── 🖼️ icon-144x144.png
│   │   ├── 🖼️ icon-152x152.png
│   │   ├── 🖼️ icon-192x192.png
│   │   ├── 🖼️ icon-384x384.png
│   │   ├── 🖼️ icon-512x512.png
│   │   ├── 🖼️ icon-72x72.png
│   │   ├── 🖼️ icon-96x96.png
│   │   ├── 🖼️ commercebox.png
│   │   ├── 🖼️ shortcut-pos.png
│   │   ├── 🖼️ shortcut-inventory.png
│   │   ├── 🖼️ shortcut-reports.png
│   │   └── 🖼️ shortcut-cash.png
│   ├── 📁 css/
│   │   ├── base.css
│   │   ├── dashboard.css
│   │   ├── pos.css
│   │   ├── inventory.css
│   │   └── reports.css
│   ├── 📁 js/
│   │   ├── pwa-install.js
│   │   ├── base.js
│   │   ├── dashboard.js
│   │   ├── pos.js
│   │   ├── inventory.js
│   │   ├── barcode-scanner.js
│   │   └── reports.js
│   └── 📁 vendor/
│       ├── bootstrap/
│       ├── jquery/
│       └── chart.js/
│
│
├── 📁 templates/
│   ├── 🌐 base.html
│   ├── 📁 authentication/
│   │   └── 🌐 login.html
│   ├── 📁 inventory/
│   │   ├── 🌐 dashboard.html
│   │   ├── 🌐 quintales_list.html
│   │   ├── 🌐 productos_list.html
│   │   ├── 🌐 add_quintal.html
│   │   └── 🌐 add_producto.html
│   ├── 📁 custom_admin/
│   │   ├── 🌐 base_admin.html
│   │   ├── 🌐 dashboard.html
│   │   ├── 🌐 usuario_confirm_delete.html
│   │   ├── 🌐 usuario_form.html
│   │   └── 🌐 usuarios_list.html
│   ├── 📁 dashboard/
│   │   ├── 🌐 admin.html
│   │   ├── 🌐 pos.html
│   │   ├── 🌐 inventory.html
│   │   └── 🌐 reports.html
│   ├── 📁 sales/
│   │   ├── 🌐 pos.html
│   │   ├── 🌐 invoice.html
│   │   ├── 🌐 sales_history.html
│   │   └── 🌐 reports.html
│   ├── 📁 financial/
│   │   ├── 🌐 dashboard.html
│   │   ├── 🌐 caja_principal.html
│   │   ├── 🌐 caja_chica.html
│   │   └── 🌐 cash_reports.html
│   ├── 📁 reports/
│   │   ├── 🌐 analytics.html
│   │   ├── 🌐 daily_report.html
│   │   ├── 🌐 monthly_report.html
│   │   ├── 🌐 inventory_report.html
│   │   └── 🌐 traceability_report.html
│   └── 📁 stock_alerts/
│       ├── 🌐 alerts_dashboard.html
│       └── 🌐 stock_status.html
│
├── 📁 tests/
│   └── 🐍 __init__.py
│
├── 📁 utils/
│   ├── 🐍 __init__.py
│   ├── 🐍 helpers.py
│   ├── 🐍 mixins.py
│   ├── 🐍 permissions.py
│   └── 🐍 validators.py
│
└── 📁 media/
    ├── 📁 barcodes/
    │   ├── quintales/
    │   └── productos/
    ├── 📁 invoices/
    ├── 📁 reports/
    └── 📁 uploads/




    📋 Descripción Funcional de Cada Módulo

🔐 1. authentication/
Propósito: Gestión completa de usuarios, roles y permisos del sistema
Funcionalidades principales:

Sistema de usuarios personalizado con roles específicos (Administrador, Supervisor, Vendedor, Cajero)
Autenticación segura con tokens y sesiones
Control de acceso granular por módulo y funcionalidad
Gestión de permisos dinámicos por rol
Auditoría de accesos con logs de login/logout
Bloqueo temporal tras intentos fallidos
Recuperación de contraseñas con tokens seguros

Casos de uso típicos:

Vendedor inicia sesión para acceder al POS
Supervisor consulta reportes de ventas
Administrador gestiona usuarios y permisos
Cajero accede solo a funciones de caja


📦 2. inventory_management/
Propósito: Núcleo del sistema dual de inventario (quintales + productos normales)
Funcionalidades principales:

Gestión de quintales con trazabilidad individual

Registro por quintal con código único
Seguimiento FIFO automático
Control de peso inicial vs actual
Trazabilidad desde origen hasta venta


Gestión de productos normales tradicionales

Stock por unidades
Categorización obligatoria
Control de marcas y proveedores


Sistema unificado de búsqueda por código de barras
Generación automática de códigos únicos
Control de stock en tiempo real con semáforos
Alertas inteligentes de stock bajo/crítico
Movimientos de inventario con auditoría completa

Casos de uso típicos:

Recepción de 50 quintales de arroz con códigos únicos
Búsqueda de producto por código de barras en POS
Alerta automática cuando quintal llega a 5kg restantes
Consulta de historial completo de un quintal específico


💰 3. sales_management/
Propósito: Sistema de ventas y POS que maneja ambos tipos de inventario
Funcionalidades principales:

POS unificado para ventas mixtas

Escaneo de códigos que identifica automáticamente el tipo
Venta simultánea de quintales y productos normales
Cálculo automático de precios según tipo
Aplicación de descuentos por categoría


Gestión de clientes con historial de compras
Facturación integrada física y electrónica
Procesamiento de pagos múltiples formas
Tickets personalizados con información de trazabilidad
Descuentos y promociones configurables
Reservas y créditos por tipo de producto

Casos de uso típicos:

Venta mixta: 2kg de arroz (quintal) + 5 latas de atún (productos normales)
Cliente frecuente recibe descuento automático
Emisión de factura electrónica con desglose por tipo
Procesamiento de pago mixto (efectivo + tarjeta)


🏦 4. financial_management/
Propósito: Control financiero con caja dual y contabilidad automática
Funcionalidades principales:

Caja principal para manejo de ventas

Apertura con monto inicial
Registro automático de todas las ventas
Desglose por tipo de inventario (quintales vs productos)
Cierre con conciliación automática


Caja chica para gastos menores

Fondo fijo configurable
Categorización de gastos (limpieza, oficina, emergencias)
Comprobantes automáticos
Alertas de reposición


Contabilidad automática

Asientos contables generados por cada venta
Desglose por quintales y productos normales
Cálculo de rentabilidad por tipo
Integración con movimientos de caja chica



Casos de uso típicos:

Apertura de caja con $500 iniciales
Registro automático de venta de $150 (80% quintales, 20% productos)
Pago de $25 en limpieza desde caja chica
Cierre de caja con conciliación automática


📊 5. reports_analytics/
Propósito: Business Intelligence y reportes ejecutivos del sistema dual
Funcionalidades principales:

Dashboard en tiempo real con métricas duales

Ventas del día por tipo de inventario
Productos estrella por categoría
Quintales más rentables
Alertas de stock crítico


Reportes de inventario

Valorización unificada (quintales + productos)
Rotación de inventario por tipo
Análisis de márgenes por categoría


Reportes de ventas

Ventas por período con desglose dual
Análisis por vendedor, cliente, categoría
Comparativas de rendimiento


Reportes financieros

Rentabilidad por quintal individual
Margen por categoría de productos
Flujo de caja unificado


Reportes de trazabilidad

Historial completo de quintales
Seguimiento origen-destino
Análisis de proveedores



Casos de uso típicos:

Dashboard muestra que arroz es el quintal más vendido hoy
Reporte semanal de rentabilidad por categoría
Análisis de trazabilidad de quintal vendido la semana pasada
Comparativa de ventas quintales vs productos normales


🖨️ 6. hardware_integration/
Propósito: Integración con hardware de punto de venta
Funcionalidades principales:

Impresoras térmicas

Tickets de venta con formato personalizado
Etiquetas de códigos de barras para quintales
Etiquetas de precios para productos normales
Reportes de cierre de caja


Escáneres de códigos de barras

Lectura automática USB/Serie
Identificación de tipo de producto por prefijo
Integración directa con POS


Básculas electrónicas

Pesaje automático para quintales
Cálculo de precio por peso
Integración con sistema de ventas


Gavetas de dinero

Apertura automática en ventas
Control de acceso por usuario
Integración con sistema de caja



Casos de uso típicos:

Escaneo de código CBX-QNT-001 abre información del quintal
Báscula registra 2.5kg y calcula precio automáticamente
Impresión de ticket con trazabilidad del quintal vendido
Apertura de gaveta al completar venta


🔔 7. notifications/
Propósito: Sistema de alertas y notificaciones inteligentes
Funcionalidades principales:

Alertas de stock

Quintales próximos a agotarse
Productos normales bajo stock mínimo
Productos próximos a vencer


Notificaciones de ventas

Ventas grandes que requieren autorización
Descuentos excesivos aplicados
Devoluciones procesadas


Alertas de sistema

Errores en facturación electrónica
Problemas de hardware
Backups automáticos completados


Notificaciones financieras

Caja chica con fondos bajos
Diferencias en arqueo de caja
Límites de crédito excedidos



Casos de uso típicos:

Alerta: "Quintal CBX-QNT-001 tiene solo 3kg restantes"
Notificación: "10 productos van a vencer en 5 días"
Alerta: "Caja chica necesita reposición de $200"
Notificación: "Venta de $500 requiere autorización de supervisor"


⚙️ 8. system_configuration/
Propósito: Configuración global y administración del sistema
Funcionalidades principales:

Configuración de inventario

Prefijos de códigos de barras
Umbrales de stock crítico/bajo
Unidades de medida disponibles
Factores de conversión (arroba, libra, kg)


Configuración de ventas

Descuentos máximos por categoría
Formas de pago aceptadas
Facturación electrónica


Configuración de hardware

Impresoras disponibles
Puertos de comunicación
Configuración de básculas


Backups y mantenimiento

Programación de respaldos automáticos
Limpieza de logs antiguos
Optimización de base de datos



Casos de uso típicos:

Configurar que alerta de stock crítico sea al 10%
Establecer descuento máximo de 15% para categoría alimentos
Configurar nueva impresora térmica en puerto USB
Programar backup diario a las 2:00 AM


👥 9. custom_admin/
Propósito: Panel de administración personalizado para CommerceBox
Funcionalidades principales:

Dashboard administrativo personalizado

Resumen ejecutivo del sistema
Métricas clave de rendimiento
Estado de salud del sistema


Gestión de usuarios avanzada

Creación/edición de usuarios
Asignación de roles y permisos
Historial de actividad por usuario


Configuración del sistema centralizada

Parámetros globales de CommerceBox
Configuración de módulos
Gestión de licencias


Herramientas de mantenimiento

Limpieza de datos antiguos
Regeneración de reportes
Monitoreo de rendimiento



Casos de uso típicos:

Administrador revisa dashboard con KPIs del mes
Creación de nuevo usuario vendedor con permisos específicos
Configuración de parámetros de facturación electrónica
Ejecución de tareas de mantenimiento programadas


🚨 10. stock_alert_system/
Propósito: Sistema de semáforos y alertas inteligentes de stock
Funcionalidades principales:

Sistema de semáforos por tipo de producto

🟢 Verde: Stock normal
🟡 Amarillo: Stock bajo
🔴 Rojo: Stock crítico
⚫ Negro: Agotado


Cálculo automático de estados

Para quintales: basado en peso restante
Para productos normales: basado en unidades vs stock mínimo


Alertas proactivas

Notificaciones antes de agotamiento
Sugerencias de reorden
Análisis de tendencias de consumo


Dashboard de alertas centralizado

Vista global de todos los productos críticos
Filtros por tipo, categoría, proveedor
Acciones rápidas de reorden



Casos de uso típicos:

Quintal de arroz pasa a amarillo cuando queda 15% del peso
Producto normal pasa a rojo cuando stock actual ≤ stock mínimo
Alerta diaria: "5 quintales y 12 productos en estado crítico"
Sugerencia automática de reorden basada en historial de ventas


🔗 Integración Entre Módulos
Flujo Principal de Operación:

Inicio de día:

authentication → Login de vendedor
financial_management → Apertura de caja principal
stock_alert_system → Revisión de alertas del día


Durante ventas:

inventory_management → Búsqueda de productos por código
sales_management → Procesamiento de venta mixta
hardware_integration → Impresión de ticket
financial_management → Registro automático en caja


Gestión de inventario:

inventory_management → Recepción de nuevos productos
stock_alert_system → Actualización automática de semáforos
notifications → Envío de alertas si es necesario


Final del día:

financial_management → Cierre de caja con conciliación
reports_analytics → Generación de reportes del día
system_configuration → Backup automático



Beneficios de la Arquitectura Modular:
✅ Escalabilidad - Cada módulo puede crecer independientemente
✅ Mantenibilidad - Cambios aislados por funcionalidad
✅ Reutilización - Servicios compartidos entre módulos
✅ Testing - Pruebas unitarias por módulo
✅ Despliegue - Actualizaciones modulares sin afectar todo el sistema
Esta arquitectura de CommerceBox permite manejar la complejidad del inventario dual manteniendo la simplicidad operativa para los usuarios finales.