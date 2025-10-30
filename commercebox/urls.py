from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.custom_admin.views import login_page_view
from apps.authentication.views import logout_view

admin.site.site_header = 'CommerceBox - Django Admin'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Administración Avanzada'

urlpatterns = [
    # ========================================
    # RUTAS PRINCIPALES
    # ========================================
    
    # Redirect raíz al login
    path('', lambda request: __import__('django.shortcuts').shortcuts.redirect('/login/')),
    
    # ✅ Login (página HTML)
    path('login/', login_page_view, name='login'),
    
    # ✅ Logout (limpia sesión y redirige al login)
    path('logout/', logout_view, name='logout'),
    
    # ========================================
    # PANEL ADMINISTRATIVO
    # ========================================
    path('panel/', include('apps.custom_admin.urls', namespace='custom_admin')),
    
    # ========================================
    # DJANGO ADMIN
    # ========================================
    path('django-admin/', admin.site.urls),
    
    # ========================================
    # APIs
    # ========================================
    
    # API de autenticación (JWT)
    path('api/auth/', include('apps.authentication.urls', namespace='authentication')),
    
    # API de inventario
    path('api/inventario/', include('apps.inventory_management.urls')),
    
    # API de ventas
    path('api/ventas/', include('apps.sales_management.urls')),
    
    # API de finanzas
    path('api/finanzas/', include('apps.financial_management.urls')),
    
    # API de reportes
    path('api/reportes/', include('apps.reports_analytics.urls')),
    
    # API de hardware
    path('api/hardware/', include('apps.hardware_integration.api.urls')),
    path('api/configuracion/', include('apps.system_configuration.urls', namespace='system_configuration')),
]

# ========================================
# ARCHIVOS ESTÁTICOS Y MEDIA (DESARROLLO)
# ========================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)