# apps/system_configuration/urls.py

"""
URLs para el módulo de configuración del sistema
"""

from django.urls import path
from . import views

app_name = 'system_configuration'

urlpatterns = [
    # ==========================================
    # DASHBOARD PRINCIPAL
    # ==========================================
    path('', views.dashboard_configuracion, name='dashboard'),
    
    # ==========================================
    # CONFIGURACIÓN GENERAL
    # ==========================================
    path('configuracion/', views.configuracion_general, name='configuracion_general'),
    path('informacion/', views.informacion_sistema, name='informacion_sistema'),
    path('exportar/', views.exportar_configuracion, name='exportar_configuracion'),
    
    # ==========================================
    # GESTIÓN DE PARÁMETROS
    # ==========================================
    path('parametros/', views.parametros_lista, name='parametros_lista'),
    path('parametros/crear/', views.parametro_crear, name='parametro_crear'),
    path('parametros/<uuid:parametro_id>/editar/', views.parametro_editar, name='parametro_editar'),
    path('parametros/<uuid:parametro_id>/eliminar/', views.parametro_eliminar, name='parametro_eliminar'),
    
    # ==========================================
    # GESTIÓN DE BACKUPS
    # ==========================================
    path('backups/', views.backups_lista, name='backups_lista'),
    path('backups/ejecutar/', views.backup_ejecutar, name='backup_ejecutar'),
    path('backups/<uuid:backup_id>/descargar/', views.backup_descargar, name='backup_descargar'),
    path('backups/<uuid:backup_id>/restaurar/', views.backup_restaurar, name='backup_restaurar'),
    
    # ==========================================
    # LOGS DE CONFIGURACIÓN
    # ==========================================
    path('logs/', views.logs_configuracion, name='logs_configuracion'),
    
    # ==========================================
    # HEALTH CHECK
    # ==========================================
    path('health-check/', views.health_check_dashboard, name='health_check_dashboard'),
    path('health-check/ejecutar/', views.health_check_ejecutar, name='health_check_ejecutar'),
    path('api/health-check/', views.health_check_api, name='health_check_api'),
]