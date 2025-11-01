from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.shortcuts import redirect
from apps.custom_admin.views import login_page_view
from apps.authentication.views import logout_view

admin.site.site_header = 'CommerceBox - Django Admin'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Administración Avanzada'


def manifest_view(request):
    """
    Vista que sirve el manifest.json para PWA
    """
    manifest_data = {
        "name": "CommerceBox - Sistema ERP/POS",
        "short_name": "CommerceBox",
        "description": "Sistema integral de gestión empresarial con punto de venta",
        "start_url": "/panel/dashboard/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#4f46e5",
        "orientation": "portrait-primary",
        "scope": "/",
        "lang": "es",
        "dir": "ltr",
        "icons": [
            {
                "src": "/static/pwa/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/pwa/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "categories": ["business", "finance", "productivity"]
    }
    return JsonResponse(manifest_data, safe=False)


def redirect_to_login(request):
    """Redirige a la página de login"""
    return redirect('/login/')


urlpatterns = [
    # ========================================
    # RUTAS PRINCIPALES
    # ========================================
    
    # Redirect raíz al login
    path('', redirect_to_login, name='home'),
    
    # ✅ Login (página HTML)
    path('login/', login_page_view, name='login'),
    
    # ✅ Logout (limpia sesión y redirige al login)
    path('logout/', logout_view, name='logout'),
    
    # ========================================
    # PWA
    # ========================================
    path('manifest.json', manifest_view, name='pwa_manifest'),
    
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

    path('panel/finanzas/', include('apps.financial_management.urls', namespace='financial_management')),
    
    path('panel/reportes-analitica/', include('apps.reports_analytics.urls', namespace='reports_analytics')),
]


# ========================================
# ARCHIVOS ESTÁTICOS Y MEDIA (DESARROLLO)
# ========================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)