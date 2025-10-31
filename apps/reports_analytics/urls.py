# apps/reports_analytics/urls.py

from django.urls import path
from . import views

app_name = 'reports_analytics'

urlpatterns = [
    # ============================================================================
    # DASHBOARD
    # ============================================================================
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/actualizar/', views.DashboardActualizarView.as_view(), name='dashboard_actualizar'),
    
    # ============================================================================
    # REPORTES DE VENTAS
    # ============================================================================
    path('ventas/', views.ReporteVentasView.as_view(), name='ventas'),
    path('ventas/periodo/', views.VentasPeriodoView.as_view(), name='ventas_periodo'),
    path('ventas/diarias/', views.VentasDiariasView.as_view(), name='ventas_diarias'),
    path('ventas/productos/', views.ProductosMasVendidosView.as_view(), name='productos_mas_vendidos'),
    path('ventas/categorias/', views.VentasCategoriasView.as_view(), name='ventas_categorias'),
    path('ventas/vendedores/', views.VentasVendedoresView.as_view(), name='ventas_vendedores'),
    path('ventas/clientes/', views.ClientesTopView.as_view(), name='clientes_top'),
    path('ventas/devoluciones/', views.DevolucionesView.as_view(), name='devoluciones'),
    path('ventas/comparativo/', views.ComparativoView.as_view(), name='comparativo'),
    
    # ============================================================================
    # REPORTES DE INVENTARIO
    # ============================================================================
    path('inventario/', views.ReporteInventarioView.as_view(), name='inventario'),
    path('inventario/valorizado/', views.InventarioValorizadoView.as_view(), name='inventario_valorizado'),
    path('inventario/categorias/', views.InventarioCategoriasView.as_view(), name='inventario_categorias'),
    path('inventario/criticos/', views.ProductosCriticosView.as_view(), name='productos_criticos'),
    path('inventario/movimientos/', views.MovimientosInventarioView.as_view(), name='movimientos_inventario'),
    path('inventario/rotacion/', views.RotacionInventarioView.as_view(), name='rotacion_inventario'),
    path('inventario/proveedores/', views.InventarioProveedoresView.as_view(), name='inventario_proveedores'),
    
    # ============================================================================
    # REPORTES FINANCIEROS
    # ============================================================================
    path('financiero/', views.ReporteFinancieroView.as_view(), name='financiero'),
    path('financiero/caja/', views.MovimientosCajaView.as_view(), name='movimientos_caja'),
    path('financiero/arqueos/', views.ArqueosCajaView.as_view(), name='arqueos_caja'),
    path('financiero/caja-chica/', views.CajaChicaView.as_view(), name='caja_chica'),
    path('financiero/rentabilidad/', views.RentabilidadView.as_view(), name='rentabilidad'),
    path('financiero/flujo-efectivo/', views.FlujoEfectivoView.as_view(), name='flujo_efectivo'),
    path('financiero/creditos/', views.CreditosPendientesView.as_view(), name='creditos_pendientes'),
    path('financiero/estado/', views.EstadoFinancieroView.as_view(), name='estado_financiero'),
    
    # ============================================================================
    # REPORTES DE TRAZABILIDAD
    # ============================================================================
    path('trazabilidad/', views.TrazabilidadView.as_view(), name='trazabilidad'),
    path('trazabilidad/quintal/<uuid:quintal_id>/', views.TrazabilidadQuintalView.as_view(), name='trazabilidad_quintal'),
    path('trazabilidad/lote/<str:lote>/', views.TrazabilidadLoteView.as_view(), name='trazabilidad_lote'),
    path('trazabilidad/proveedor/<uuid:proveedor_id>/', views.TrazabilidadProveedorView.as_view(), name='trazabilidad_proveedor'),
    path('trazabilidad/fifo/<uuid:producto_id>/', views.FlujoFIFOView.as_view(), name='flujo_fifo'),
    path('trazabilidad/ciclo-vida/', views.CicloVidaQuintalesView.as_view(), name='ciclo_vida'),
    
    # ============================================================================
    # EXPORTACIÓN DE REPORTES
    # ============================================================================
    path('exportar/pdf/<str:tipo_reporte>/', views.ExportarPDFView.as_view(), name='exportar_pdf'),
    path('exportar/excel/<str:tipo_reporte>/', views.ExportarExcelView.as_view(), name='exportar_excel'),
    path('exportar/csv/<str:tipo_reporte>/', views.ExportarCSVView.as_view(), name='exportar_csv'),
    
    # ============================================================================
    # REPORTES GUARDADOS
    # ============================================================================
    path('guardados/', views.ReportesGuardadosView.as_view(), name='reportes_guardados'),
    path('guardados/<uuid:reporte_id>/', views.ReporteDetalleView.as_view(), name='reporte_detalle'),
    path('guardados/<uuid:reporte_id>/descargar/', views.DescargarReporteView.as_view(), name='descargar_reporte'),
    
    # ============================================================================
    # CONFIGURACIÓN
    # ============================================================================
    path('configuracion/', views.ConfiguracionReportesView.as_view(), name='configuracion'),
    path('configuracion/guardar/', views.GuardarConfiguracionView.as_view(), name='guardar_configuracion'),
    
    # ============================================================================
    # API ENDPOINTS (JSON)
    # ============================================================================
    path('api/dashboard/', views.DashboardAPIView.as_view(), name='dashboard_api'),
    path('api/ventas/grafico/', views.VentasGraficoAPIView.as_view(), name='ventas_grafico_api'),
    path('api/inventario/estado/', views.InventarioEstadoAPIView.as_view(), name='inventario_estado_api'),
]