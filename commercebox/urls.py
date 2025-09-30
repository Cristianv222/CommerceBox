"""
CommerceBox - URLs principales del proyecto
Configuración de rutas para todos los módulos
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ========================================
    # ADMIN DE DJANGO
    # ========================================
    path('admin/', admin.site.urls),
    
    # ========================================
    # API DE AUTENTICACIÓN
    # ========================================
    path('api/auth/', include('apps.authentication.urls', namespace='authentication')),
    
    # ========================================
    # API DE MÓDULOS DE COMMERCEBOX
    # ========================================
    
    # Gestión de inventario
    path('api/inventario/', include('apps.inventory_management.urls', namespace='inventory')),
    
    # Gestión de ventas
    path('api/ventas/', include('apps.sales_management.urls', namespace='sales')),
    
    # Gestión financiera
    # path('api/finanzas/', include('apps.financial_management.urls', namespace='financial')),
    
    # Reportes y analytics
    # path('api/reportes/', include('apps.reports_analytics.urls', namespace='reports')),
    
    # Integración de hardware
    # path('api/hardware/', include('apps.hardware_integration.urls', namespace='hardware')),
    
    # Notificaciones
    # path('api/notificaciones/', include('apps.notifications.urls', namespace='notifications')),
    
    # Configuración del sistema
    # path('api/configuracion/', include('apps.system_configuration.urls', namespace='configuration')),
    
    # Sistema de alertas de stock
    # path('api/alertas/', include('apps.stock_alert_system.urls', namespace='stock_alerts')),
    
    # ========================================
    # FRONTEND (OPCIONAL)
    # ========================================
    path('', include('apps.custom_admin.urls', namespace='custom_admin')),
]

# ========================================
# CONFIGURACIÓN PARA DESARROLLO
# ========================================
if settings.DEBUG:
    # Servir archivos media en desarrollo
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Servir archivos estáticos en desarrollo
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ========================================
# PERSONALIZACIÓN DEL ADMIN
# ========================================
admin.site.site_header = 'CommerceBox - Administración'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Panel de Control'