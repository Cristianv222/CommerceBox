from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.shortcuts import redirect
from django.db import connection as db_connection
from apps.custom_admin.views import login_page_view
from apps.authentication.views import logout_view
from apps.hardware_integration.api import agente_views  # 🔧 NUEVO: Import para captura de URLs
from .health import health_check

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


def health_check(request):
    """Health check endpoint para Docker. Sin autenticación."""
    try:
        db_connection.ensure_connection()
        return JsonResponse({"status": "ok", "db": "connected"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "error", "detail": str(e)}, status=503)


urlpatterns = [
    # ========================================
    # RUTAS PRINCIPALES
    # ========================================
    
    # Health check para Docker (sin autenticación requerida)
    path('health/', health_check, name='health_check_root'),
    
    # Redirect raíz al login
    path('', redirect_to_login, name='home'),
    # Health Check
    path('health/', health_check, name='health_check'),
    
    # ✅ Login (página HTML)
    path('login/', login_page_view, name='login'),
    
    # ✅ Logout (limpia sesión y redirige al login)
    path('logout/', logout_view, name='logout'),
    
    # ========================================
    # PWA
    # ========================================
    path('manifest.json', manifest_view, name='pwa_manifest'),
    
    # ========================================
    # PANEL ADMINISTRATIVO Y MÓDULOS DEL PANEL
    # ========================================
    # Mapear reportes ANTES del panel general para que no haya conflictos 404
    path('panel/reportes-analitica/', include('apps.reports_analytics.urls', namespace='reports_analytics')),
    
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
    path('api/finanzas/', include('apps.financial_management.urls', namespace='financial_management')),
    
    # (Reportes movido arriba dentro de panel/)
    # path('api/reportes/', include('apps.reports_analytics.urls', namespace='reports_analytics')),
    
    # API de hardware
    path('api/hardware/', include('apps.hardware_integration.api.urls')),
    
    path('api/configuracion/', include('apps.system_configuration.urls', namespace='system_configuration')),
    
    # Mapeo de facturación electrónica
    path('sri/', include('apps.electronic_invoicing.urls', namespace='electronic_invoicing')),
    
    # ========================================
    # 🔧 CAPTURA DE URLs MALFORMADAS - AGENTE .EXE
    # ========================================
    # El agente .exe siempre agrega /api/hardware/agente/trabajos/ al final de la URL configurada
    # Por eso necesitamos capturar todas las combinaciones posibles
    
    # Captura: //api/hardware/agente/trabajos/ (doble slash al inicio)
    re_path(r'^/?api/hardware/agente/trabajos/?$', agente_views.obtener_trabajos_pendientes, name='captura_trabajos_doble_slash'),
    
    # Captura: //api/hardware/agente/registrar/
    re_path(r'^/?api/hardware/agente/registrar/?$', agente_views.registrar_agente, name='captura_registrar'),
    
    # Captura: /api/hardware/agente/trabajos-debug//api/hardware/agente/trabajos/
    re_path(r'^/?api/hardware/agente/trabajos-debug/.+$', agente_views.obtener_trabajos_pendientes, name='captura_trabajos_debug'),
    
    # Captura: /api/hardware/agente/trabajos//api/hardware/agente/trabajos/ (duplicación)
    re_path(r'^/?api/hardware/agente/trabajos/.+agente/trabajos/?$', agente_views.obtener_trabajos_pendientes, name='captura_trabajos_duplicado'),
    
    # Captura: cualquier cosa que termine en /api/hardware/agente/trabajos/
    re_path(r'^.+/api/hardware/agente/trabajos/?$', agente_views.obtener_trabajos_pendientes, name='captura_trabajos_general'),
    
    # Captura cualquier variación con múltiples slashes
    re_path(r'^api/hardware/agente/estado/?$', agente_views.obtener_estado_agente, name='captura_estado'),
    re_path(r'^api/hardware/agente/resultado/?$', agente_views.reportar_resultado, name='captura_resultado'),

]


# ========================================
# ARCHIVOS ESTÁTICOS Y MEDIA (DESARROLLO)
# ========================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

