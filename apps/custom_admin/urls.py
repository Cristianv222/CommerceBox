# apps/custom_admin/urls.py

from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # ========================================
    # DASHBOARD PRINCIPAL
    # ========================================
    path('', views.dashboard_view, name='dashboard'),
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/alertas/count/', views.api_alertas_count, name='api_alertas_count'),
    
    # ========================================
    # USUARIOS Y ROLES
    # ========================================
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('roles/', views.roles_view, name='roles'),
    
    # ========================================
    # PUNTO DE VENTA (POS)
    # ========================================
    path('pos/', views.pos_view, name='pos'),
    
    # APIs para POS
    path('api/productos/buscar/', views.api_buscar_productos, name='api_buscar_productos'),
    path('api/productos/<uuid:producto_id>/', views.api_obtener_producto, name='api_obtener_producto'),
    path('api/ventas/procesar/', views.api_procesar_venta, name='api_procesar_venta'),
    path('api/ventas/<uuid:venta_id>/detalle/', views.api_venta_detalle, name='api_venta_detalle'),
    
    # ========================================
    # INVENTARIO - Dashboard
    # ========================================
    path('inventario/', views.inventario_dashboard_view, name='inventario'),
    
    # ========================================
    # INVENTARIO - Productos
    # ========================================
    path('inventario/productos/', views.productos_view, name='productos'),
    path('inventario/productos/crear/', views.producto_crear, name='producto_crear'),
    path('inventario/productos/<uuid:pk>/', views.producto_detail_view, name='producto_detail'),
    path('inventario/productos/<uuid:producto_id>/editar/', views.producto_editar, name='producto_editar'),
    path('inventario/productos/<uuid:producto_id>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    
    # APIs para productos
    path('api/productos/buscar-codigo/', views.api_buscar_producto_codigo, name='api_buscar_codigo'),
    
    # ========================================
    # INVENTARIO - Quintales
    # ========================================
    path('inventario/quintales/', views.quintales_view, name='quintales'),
    path('inventario/quintales/<uuid:pk>/', views.quintal_detail_view, name='quintal_detail'),
    
    # ========================================
    # INVENTARIO - Categorías
    # ========================================
    path('inventario/categorias/', views.categorias_view, name='categorias'),
    path('inventario/categorias/crear/', views.categoria_crear_view, name='categoria_crear'),
    path('inventario/categorias/<uuid:pk>/editar/', views.categoria_editar_view, name='categoria_editar'),
    path('inventario/categorias/<uuid:pk>/eliminar/', views.categoria_eliminar_view, name='categoria_eliminar'),
    
    # ========================================
    # INVENTARIO - Marcas
    # ========================================
    path('inventario/marcas/', views.marcas_list, name='marcas'),
    path('inventario/marcas/crear/', views.marca_crear, name='marca_crear'),
    path('inventario/marcas/<uuid:pk>/editar/', views.marca_editar, name='marca_editar'),
    path('inventario/marcas/<uuid:pk>/eliminar/', views.marca_eliminar, name='marca_eliminar'),
    
    # ========================================
    # INVENTARIO - Proveedores
    # ========================================
    path('inventario/proveedores/', views.proveedores_view, name='proveedores'),
    path('inventario/proveedores/crear/', views.proveedor_crear, name='proveedor_crear'),
    path('inventario/proveedores/<uuid:pk>/editar/', views.proveedor_editar, name='proveedor_editar'),
    path('inventario/proveedores/<uuid:pk>/eliminar/', views.proveedor_eliminar, name='proveedor_eliminar'),
    
    # API para proveedores
    path('api/proveedores/<uuid:pk>/detalle/', views.proveedor_detalle_api, name='proveedor_detalle_api'),
    
    # ========================================
    # INVENTARIO - Movimientos
    # ========================================
    path('inventario/movimientos/', views.movimientos_inventario_view, name='movimientos_inventario'),
    
    # API para detalles del movimiento
    path('api/movimientos/<uuid:pk>/info/', views.movimiento_detalle_api, name='movimiento_detalle_api'),
    
    # Exportación individual
    path('inventario/movimientos/<uuid:pk>/export/excel/', views.exportar_movimiento_excel, name='exportar_movimiento_excel'),
    path('inventario/movimientos/<uuid:pk>/export/pdf/', views.exportar_movimiento_pdf, name='exportar_movimiento_pdf'),
    
    # Exportación general (CORREGIDO: usar singular)
    path('inventario/movimientos/export-all/excel/', views.exportar_movimiento_excel, name='exportar_movimientos_excel'),
    path('inventario/movimientos/export-all/pdf/', views.exportar_movimiento_pdf, name='exportar_movimientos_pdf'),
    
    # ========================================
    # INVENTARIO - Entrada de Inventario
    # ========================================
    path('inventario/entrada/', views.entrada_inventario_view, name='entrada_inventario'),
    
    # ✅ APIs para Entrada de Inventario (CORREGIDAS)
    path('api/inventario/procesar-entrada-unificada/', views.api_procesar_entrada_unificada, name='api_procesar_entrada_unificada'),
    path('api/inventario/quintales-disponibles/', views.api_quintales_disponibles, name='api_quintales_disponibles'),
    path('api/inventario/procesar-entrada/', views.api_procesar_entrada_masiva, name='api_procesar_entrada'),
    path('api/inventario/generar-pdf-codigos/', views.api_generar_pdf_codigos, name='api_generar_pdf_codigos'),
    
    # ========================================
    # VENTAS - Dashboard
    # ========================================
    path('ventas/', views.ventas_dashboard_view, name='ventas'),
    path('ventas/historial/', views.ventas_view, name='ventas_list'),
    
    # ========================================
    # VENTAS - Detalle y Acciones
    # ========================================
    path('ventas/<uuid:pk>/', views.venta_detail_view, name='venta_detail'),
    path('ventas/<uuid:pk>/anular/', views.venta_anular_view, name='venta_anular'),
    path('ventas/<uuid:pk>/ticket/', views.venta_ticket_view, name='venta_ticket'),
    path('ventas/<uuid:pk>/factura/', views.venta_factura_view, name='venta_factura'),
    
    # API para detalles de venta
    path('api/ventas/<uuid:pk>/info/', views.venta_detalle_api, name='venta_detalle_api'),
    
    # ========================================
    # VENTAS - Exportación Individual
    # ========================================
    path('ventas/<uuid:pk>/export/excel/', views.exportar_venta_excel_individual, name='exportar_venta_excel'),
    path('ventas/<uuid:pk>/export/pdf/', views.exportar_venta_pdf_individual, name='exportar_venta_pdf'),
    
    # ========================================
    # VENTAS - Exportación General
    # ========================================
    path('ventas/export-all/excel/', views.exportar_ventas_excel_general, name='exportar_ventas_excel_general'),
    path('ventas/export-all/pdf/', views.exportar_ventas_pdf_general, name='exportar_ventas_pdf_general'),
    
    # Rutas antiguas (mantener por compatibilidad)
    path('ventas/export/excel/', views.ventas_export_excel, name='ventas_export_excel'),
    path('ventas/export/pdf/', views.ventas_export_pdf, name='ventas_export_pdf'),
    
    # ========================================
    # VENTAS - Clientes y Devoluciones
    # ========================================
    path('ventas/clientes/', views.clientes_view, name='clientes'),
    path('ventas/devoluciones/', views.devoluciones_view, name='devoluciones'),
    
    # ========================================
    # FINANZAS
    # ========================================
    path('finanzas/', views.finanzas_dashboard_view, name='finanzas'),
    path('finanzas/cajas/', views.cajas_view, name='cajas'),
    path('finanzas/cajas/<uuid:pk>/', views.caja_detail_view, name='caja_detail'),
    path('finanzas/arqueos/', views.arqueos_view, name='arqueos'),
    path('finanzas/caja-chica/', views.caja_chica_view, name='caja_chica'),
    
    # ========================================
    # REPORTES
    # ========================================
    path('reportes/', views.reportes_dashboard_view, name='reportes'),
    path('reportes/ventas/', views.reporte_ventas_view, name='reporte_ventas'),
    path('reportes/inventario/', views.reporte_inventario_view, name='reporte_inventario'),
    path('reportes/financiero/', views.reporte_financiero_view, name='reporte_financiero'),
    
    # ========================================
    # ALERTAS Y NOTIFICACIONES
    # ========================================
    path('alertas/', views.alertas_view, name='alertas'),
    path('notificaciones/', views.notificaciones_view, name='notificaciones'),
    
    # ========================================
    # LOGS Y AUDITORÍA
    # ========================================
    path('logs/', views.logs_view, name='logs'),
    path('logs/accesos/', views.logs_accesos_view, name='logs_accesos'),
    
    # ========================================
    # SESIONES
    # ========================================
    path('sesiones/', views.sesiones_view, name='sesiones'),
    
    # ========================================
    # CONFIGURACIÓN
    # ========================================
    path('configuracion/', views.configuracion_view, name='configuracion'),
    path('configuracion/empresa/', views.config_empresa_view, name='config_empresa'),
    path('configuracion/facturacion/', views.config_facturacion_view, name='config_facturacion'),
    
    # ========================================
    # BÚSQUEDA GLOBAL
    # ========================================
    path('busqueda/', views.busqueda_view, name='busqueda'),
    
    # ========================================
    # PERFIL DE USUARIO
    # ========================================
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/editar/', views.perfil_editar_view, name='perfil_editar'),
    path('perfil/cambiar-password/', views.perfil_cambiar_password_view, name='perfil_cambiar_password'),
    
    # ========================================
    # HEALTH CHECK
    # ========================================
    path('health/', views.health_check_view, name='health_check'),
    # ========================================
    # APIs PARA QUINTALES
    # ========================================
    path('api/productos/<uuid:producto_id>/quintales/', views.api_quintales_por_producto, name='api_quintales_por_producto'),
    path('api/quintales/calcular/', views.api_calcular_quintal, name='api_calcular_quintal'),
]