from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Usuarios y Roles
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('roles/', views.roles_view, name='roles'),
    
    # Inventario
    path('inventario/', views.inventario_dashboard_view, name='inventario'),
    path('inventario/productos/', views.productos_view, name='productos'),
    path('inventario/quintales/', views.quintales_view, name='quintales'),
    path('inventario/categorias/', views.categorias_view, name='categorias'),
    path('inventario/categorias/crear/', views.categoria_crear_view, name='categoria_crear'),
    path('inventario/categorias/<uuid:pk>/editar/', views.categoria_editar_view, name='categoria_editar'),
    path('inventario/categorias/<uuid:pk>/eliminar/', views.categoria_eliminar_view, name='categoria_eliminar'),
    path('inventario/proveedores/', views.proveedores_view, name='proveedores'),
    
    # CRUD Productos
    path('inventario/productos/crear/', views.producto_crear, name='producto_crear'),
    path('inventario/productos/<uuid:producto_id>/editar/', views.producto_editar, name='producto_editar'),
    path('inventario/productos/<uuid:producto_id>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    
    # Ventas
    path('ventas/', views.ventas_dashboard_view, name='ventas'),
    path('ventas/historial/', views.ventas_view, name='ventas_list'),
    path('ventas/clientes/', views.clientes_view, name='clientes'),
    path('ventas/devoluciones/', views.devoluciones_view, name='devoluciones'),
    
    # Finanzas
    path('finanzas/', views.finanzas_dashboard_view, name='finanzas'),
    path('finanzas/cajas/', views.cajas_view, name='cajas'),
    path('finanzas/arqueos/', views.arqueos_view, name='arqueos'),
    path('finanzas/caja-chica/', views.caja_chica_view, name='caja_chica'),
    
    # Reportes
    path('reportes/', views.reportes_dashboard_view, name='reportes'),
    path('reportes/ventas/', views.reporte_ventas_view, name='reporte_ventas'),
    path('reportes/inventario/', views.reporte_inventario_view, name='reporte_inventario'),
    path('reportes/financiero/', views.reporte_financiero_view, name='reporte_financiero'),
    
    # Alertas y Logs
    path('alertas/', views.alertas_view, name='alertas'),
    path('logs/', views.logs_view, name='logs'),
    path('logs/accesos/', views.logs_accesos_view, name='logs_accesos'),
    
    # Sesiones
    path('sesiones/', views.sesiones_view, name='sesiones'),
    
    # Configuración
    path('configuracion/', views.configuracion_view, name='configuracion'),
    path('configuracion/empresa/', views.config_empresa_view, name='config_empresa'),
    path('configuracion/facturacion/', views.config_facturacion_view, name='config_facturacion'),
    
    # Búsqueda
    path('busqueda/', views.busqueda_view, name='busqueda'),
    
    # Notificaciones
    path('notificaciones/', views.notificaciones_view, name='notificaciones'),
    
    # Perfil
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/editar/', views.perfil_editar_view, name='perfil_editar'),
    path('perfil/cambiar-password/', views.perfil_cambiar_password_view, name='perfil_cambiar_password'),
    
    # APIs Mock
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    
    # Health Check
    path('health/', views.health_check_view, name='health_check'),
]