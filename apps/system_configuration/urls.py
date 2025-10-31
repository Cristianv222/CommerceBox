# apps/system_configuration/urls.py

"""
URLs para el módulo de configuración del sistema
"""

from django.urls import path
from . import views

app_name = 'system_configuration'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_configuracion, name='dashboard'),
    
    # Configuración general
    path('general/', views.configuracion_general, name='configuracion_general'),
    path('informacion/', views.informacion_sistema, name='informacion_sistema'),
    path('exportar/', views.exportar_configuracion, name='exportar_configuracion'),
    
    # ============================================================================
    # PARÁMETROS - ACTUALIZADO PARA MODALES
    # ============================================================================
    path('parametros/', views.parametros_lista, name='parametros_lista'),
    path('parametros/crear/', views.parametro_crear, name='parametro_crear'),
    
    # ✅ NUEVO: Endpoint API para obtener datos del parámetro en JSON
    path('api/parametros/<uuid:parametro_id>/', views.parametro_detalle_json, name='parametro_detalle_json'),
    
    # Editar y eliminar
    path('parametros/<uuid:parametro_id>/editar/', views.parametro_editar, name='parametro_editar'),
    path('parametros/<uuid:parametro_id>/eliminar/', views.parametro_eliminar, name='parametro_eliminar'),
    
    # Backups
    path('backups/', views.backups_lista, name='backups_lista'),
    path('backups/ejecutar/', views.backup_ejecutar, name='backup_ejecutar'),
    path('backups/<uuid:backup_id>/descargar/', views.backup_descargar, name='backup_descargar'),
    path('backups/<uuid:backup_id>/restaurar/', views.backup_restaurar, name='backup_restaurar'),
    
    # Logs
    path('logs/', views.logs_configuracion, name='logs_configuracion'),
    path('logs/<uuid:log_id>/detalle/', views.log_detalle_json, name='log_detalle_json'),
    
    # Health Check
    path('health-check/', views.health_check_dashboard, name='health_check_dashboard'),
    path('health-check/ejecutar/', views.health_check_ejecutar, name='health_check_ejecutar'),
    path('api/health-check/', views.health_check_api, name='health_check_api'),
    # ✅ NUEVAS RUTAS: APIs para dashboard (JSON)
    path('api/dashboard/backups/', views.api_backups_dashboard, name='api_dashboard_backups'),
    path('api/dashboard/logs/', views.api_logs_dashboard, name='api_dashboard_logs'),

]