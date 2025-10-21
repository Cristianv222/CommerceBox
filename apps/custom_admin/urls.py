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
    
    # ✅ NUEVO: API para reimpresión de tickets
    path('api/ventas/<uuid:venta_id>/reimprimir-ticket/', views.api_reimprimir_ticket, name='api_reimprimir_ticket'),
    
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
    
    # APIs para quintales
    path('api/productos/<uuid:producto_id>/quintales/', views.api_quintales_por_producto, name='api_quintales_por_producto'),
    path('api/quintales/calcular/', views.api_calcular_quintal, name='api_calcular_quintal'),
    
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
    
    # ✅ CORREGIDO: Exportación general de movimientos
    path('inventario/movimientos/export-all/excel/', views.exportar_movimientos_excel_general, name='exportar_movimientos_excel_general'),
    path('inventario/movimientos/export-all/pdf/', views.exportar_movimientos_pdf_general, name='exportar_movimientos_pdf_general'),
    
    # ========================================
    # INVENTARIO - Entrada de Inventario
    # ========================================
    path('inventario/entrada/', views.entrada_inventario_view, name='entrada_inventario'),
    
    # APIs para Entrada de Inventario
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
    # VENTAS - Clientes
    # ========================================
    path('ventas/clientes/', views.clientes_view, name='clientes'),
    path('ventas/clientes/crear/', views.cliente_crear, name='cliente_crear'),
    path('ventas/clientes/<uuid:pk>/editar/', views.cliente_editar, name='cliente_editar'),
    path('ventas/clientes/<uuid:pk>/eliminar/', views.cliente_eliminar, name='cliente_eliminar'),
    
    # APIs de clientes
    path('api/clientes/', views.api_clientes_list, name='api_clientes_list'),
    path('api/clientes/<uuid:pk>/', views.api_cliente_detail, name='api_cliente_detail'),
    
    # ========================================
    # VENTAS - Devoluciones
    # ========================================
    path('ventas/devoluciones/', views.devoluciones_view, name='devoluciones'),
    path('ventas/devoluciones/crear/', views.devolucion_crear, name='devolucion_crear'),
    path('ventas/devoluciones/<uuid:devolucion_id>/aprobar/', views.devolucion_aprobar, name='devolucion_aprobar'),
    
    # APIs de devoluciones
    path('api/devoluciones/', views.api_devoluciones_list, name='api_devoluciones_list'),
    path('api/devoluciones/<uuid:devolucion_id>/', views.devolucion_detalle, name='devolucion_detalle'),
    path('api/ventas/buscar/<str:numero>/', views.api_buscar_venta, name='api_buscar_venta'),
    
    # ========================================
    # FINANZAS - Dashboard
    # ========================================
    path('finanzas/', views.finanzas_dashboard_view, name='finanzas'),
    
    # ========================================
    # FINANZAS - Cajas
    # ========================================
    path('finanzas/cajas/', views.cajas_list, name='cajas_list'),
    path('finanzas/cajas/crear/', views.crear_caja, name='crear_caja'),
    path('finanzas/cajas/<uuid:caja_id>/abrir/', views.abrir_caja, name='abrir_caja'),
    path('finanzas/cajas/<uuid:caja_id>/cerrar/', views.cerrar_caja, name='cerrar_caja'),
    path('finanzas/cajas/<uuid:caja_id>/movimientos/', views.movimientos_caja, name='movimientos_caja'),
    path('finanzas/cajas/<uuid:caja_id>/movimiento/', views.crear_movimiento, name='crear_movimiento'),
    
    # ========================================
    # FINANZAS - Arqueos
    # ========================================
    path('finanzas/arqueos/', views.arqueos_list, name='arqueos_list'),
    path('finanzas/arqueos/<uuid:arqueo_id>/', views.arqueo_detalle, name='arqueo_detalle'),
    
    # ========================================
    # FINANZAS - Caja Chica
    # ========================================
    path('finanzas/caja-chica/', views.caja_chica_list, name='caja_chica_list'),
    path('finanzas/caja-chica/crear/', views.crear_caja_chica, name='crear_caja_chica'),
    path('finanzas/caja-chica/<uuid:caja_chica_id>/gasto/', views.registrar_gasto_caja_chica, name='registrar_gasto_caja_chica'),
    path('finanzas/caja-chica/<uuid:caja_chica_id>/reponer/', views.reponer_caja_chica, name='reponer_caja_chica'),
    
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
]