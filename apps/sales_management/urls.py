# apps/sales_management/urls.py

from django.urls import path
from . import views

app_name = 'sales_management'

urlpatterns = [
    # Dashboard
    path('', views.SalesDashboardView.as_view(), name='dashboard'),
    
    # Clientes
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/crear/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<uuid:pk>/', views.ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<uuid:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<uuid:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='cliente_delete'),
    path('clientes/autocomplete/', views.ClienteAutocompleteView.as_view(), name='cliente_autocomplete'),
    
    # POS (Punto de Venta)
    path('pos/', views.POSView.as_view(), name='pos'),
    path('pos/buscar-producto/', views.BuscarProductoPOSView.as_view(), name='pos_buscar_producto'),
    path('pos/agregar-carrito/', views.AgregarProductoCarritoView.as_view(), name='pos_agregar_carrito'),
    path('pos/eliminar-item/<int:index>/', views.EliminarItemCarritoView.as_view(), name='pos_eliminar_item'),
    path('pos/vaciar-carrito/', views.VaciarCarritoView.as_view(), name='pos_vaciar_carrito'),
    path('pos/procesar-venta/', views.ProcesarVentaPOSView.as_view(), name='pos_procesar_venta'),
    
    # Ventas
    path('ventas/', views.VentaListView.as_view(), name='venta_list'),
    path('ventas/<uuid:pk>/', views.VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<uuid:pk>/anular/', views.AnularVentaView.as_view(), name='venta_anular'),
    path('ventas/<uuid:pk>/ticket/', views.ImprimirTicketView.as_view(), name='venta_ticket'),
    path('ventas/<uuid:pk>/factura/', views.ImprimirFacturaView.as_view(), name='venta_factura'),
    
    # Devoluciones
    path('devoluciones/', views.DevolucionListView.as_view(), name='devolucion_list'),
    path('devoluciones/crear/', views.DevolucionCreateView.as_view(), name='devolucion_create'),
    path('devoluciones/<uuid:pk>/', views.DevolucionDetailView.as_view(), name='devolucion_detail'),
    path('devoluciones/<uuid:pk>/aprobar/', views.AprobarDevolucionView.as_view(), name='devolucion_aprobar'),
    
    # Reportes
    path('reportes/ventas/', views.ReporteVentasView.as_view(), name='reporte_ventas'),
    path('reportes/diario/', views.ReporteDiarioView.as_view(), name='reporte_diario'),
    
    # API
    path('api/estadisticas/', views.VentaEstadisticasAPIView.as_view(), name='api_estadisticas'),
    
    # ============================================================================
    # 🆕 NUEVAS API - IMPRESIÓN Y PROCESAMIENTO DE VENTAS
    # ============================================================================
    
    # Verificar estado de impresión de un ticket
    path(
        'verificar-impresion/<uuid:venta_id>/',
        views.VerificarEstadoImpresionView.as_view(),
        name='verificar_impresion'
    ),
    
    # Procesar venta completa vía API (AJAX)
    path(
        'api/procesar/',
        views.ProcesarVentaAPIView.as_view(),
        name='procesar_venta_api'
    ),
    
    # Reimprimir ticket de una venta
    path(
        'ventas/<uuid:venta_id>/reimprimir-ticket/',
        views.ReimprimirTicketView.as_view(),
        name='reimprimir_ticket'
    ),
]