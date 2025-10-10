# apps/custom_admin/urls.py

from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Usuarios y Roles
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('roles/', views.roles_view, name='roles'),
    
    # ========================================
    # PUNTO DE VENTA (NUEVO)
    # ========================================
    path('pos/', views.pos_view, name='pos'),
    
    # APIs para POS
    path('api/productos/buscar/', views.api_buscar_productos, name='api_buscar_productos'),
    path('api/productos/<uuid:producto_id>/', views.api_obtener_producto, name='api_obtener_producto'),
    path('api/ventas/procesar/', views.api_procesar_venta, name='api_procesar_venta'),
    path('api/ventas/<uuid:venta_id>/detalle/', views.api_venta_detalle, name='api_venta_detalle'),
    
    # Inventario
    path('inventario/', views.inventario_dashboard_view, name='inventario'),
    path('inventario/productos/', views.productos_view, name='productos'),
    path('inventario/productos/<uuid:pk>/', views.producto_detail_view, name='producto_detail'),
    path('inventario/productos/crear/', views.producto_crear, name='producto_crear'),
    path('inventario/productos/<uuid:producto_id>/editar/', views.producto_editar, name='producto_editar'),
    path('inventario/productos/<uuid:producto_id>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    
    path('inventario/quintales/', views.quintales_view, name='quintales'),
    path('inventario/quintales/<uuid:pk>/', views.quintal_detail_view, name='quintal_detail'),
    
    path('inventario/categorias/', views.categorias_view, name='categorias'),
    path('inventario/categorias/crear/', views.categoria_crear_view, name='categoria_crear'),
    path('inventario/categorias/<uuid:pk>/editar/', views.categoria_editar_view, name='categoria_editar'),
    path('inventario/categorias/<uuid:pk>/eliminar/', views.categoria_eliminar_view, name='categoria_eliminar'),
    
    path('inventario/proveedores/', views.proveedores_view, name='proveedores'),
    
    # ========================================
    # ENTRADA DE INVENTARIO UNIFICADA
    # ========================================
    path('inventario/entrada/', views.entrada_inventario_view, name='entrada_inventario'),
    
    # APIs para Entrada de Inventario
    path('api/inventario/procesar-entrada-unificada/', views.api_procesar_entrada_unificada, name='api_procesar_entrada_unificada'),  # ✅ NUEVA URL
    path('api/inventario/procesar-entrada/', views.api_procesar_entrada_masiva, name='api_procesar_entrada'),
    path('api/inventario/generar-pdf-codigos/', views.api_generar_pdf_codigos, name='api_generar_pdf_codigos'),
    path('api/productos/buscar-codigo/', views.api_buscar_producto_codigo, name='api_buscar_codigo'),
    
    # Ventas
    path('ventas/', views.ventas_dashboard_view, name='ventas'),
    path('ventas/historial/', views.ventas_view, name='ventas_list'),
    path('ventas/export/excel/', views.ventas_export_excel, name='ventas_export_excel'),
    path('ventas/export/pdf/', views.ventas_export_pdf, name='ventas_export_pdf'),
    path('ventas/<uuid:pk>/anular/', views.venta_anular_view, name='venta_anular'),
    path('ventas/<uuid:pk>/ticket/', views.venta_ticket_view, name='venta_ticket'),
    path('ventas/<uuid:pk>/factura/', views.venta_factura_view, name='venta_factura'),
    path('ventas/clientes/', views.clientes_view, name='clientes'),
    path('ventas/devoluciones/', views.devoluciones_view, name='devoluciones'),
    
    # Finanzas
    path('finanzas/', views.finanzas_dashboard_view, name='finanzas'),
    path('finanzas/cajas/', views.cajas_view, name='cajas'),
    path('finanzas/cajas/<uuid:pk>/', views.caja_detail_view, name='caja_detail'),
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