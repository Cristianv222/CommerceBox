# CommerceBox - Script de Inicializacion del Proyecto
# Sistema de Inventario Comercial Dual

Write-Host ">> Inicializando CommerceBox..." -ForegroundColor Green

# Crear estructura principal
$directories = @(
    "apps",
    "apps/authentication",
    "apps/authentication/management",
    "apps/authentication/management/commands",
    "apps/authentication/migrations",
    "apps/inventory_management",
    "apps/inventory_management/management",
    "apps/inventory_management/management/commands",
    "apps/inventory_management/migrations",
    "apps/inventory_management/services",
    "apps/inventory_management/utils",
    "apps/sales_management",
    "apps/sales_management/pos",
    "apps/sales_management/invoicing",
    "apps/sales_management/migrations",
    "apps/financial_management",
    "apps/financial_management/cash_management",
    "apps/financial_management/accounting",
    "apps/financial_management/migrations",
    "apps/reports_analytics",
    "apps/reports_analytics/generators",
    "apps/reports_analytics/migrations",
    "apps/hardware_integration",
    "apps/hardware_integration/printers",
    "apps/hardware_integration/scanners",
    "apps/hardware_integration/scales",
    "apps/hardware_integration/cash_drawer",
    "apps/notifications",
    "apps/notifications/services",
    "apps/notifications/migrations",
    "apps/system_configuration",
    "apps/system_configuration/management",
    "apps/system_configuration/management/commands",
    "apps/system_configuration/migrations",
    "apps/custom_admin",
    "apps/stock_alert_system",
    "apps/stock_alert_system/management",
    "apps/stock_alert_system/management/commands",
    "apps/stock_alert_system/migrations",
    "apps/stock_alert_system/utils",
    "commercebox",
    "static",
    "static/icons",
    "static/css",
    "static/js",
    "static/vendor",
    "templates",
    "templates/authentication",
    "templates/inventory",
    "templates/custom_admin",
    "templates/dashboard",
    "templates/sales",
    "templates/financial",
    "templates/reports",
    "templates/stock_alerts",
    "tests",
    "utils",
    "media",
    "media/barcodes",
    "media/barcodes/quintales",
    "media/barcodes/productos",
    "media/invoices",
    "media/reports",
    "media/uploads",
    "logs"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Write-Host "   Creado: $dir" -ForegroundColor Blue
}

Write-Host ">> Estructura de directorios creada exitosamente!" -ForegroundColor Green
Write-Host ">> Ejecutar: pip install -r requirements.txt" -ForegroundColor Yellow
Write-Host ">> Ejecutar: python manage.py migrate" -ForegroundColor Yellow
Write-Host ">> Ejecutar: python manage.py setup_commercebox" -ForegroundColor Yellow