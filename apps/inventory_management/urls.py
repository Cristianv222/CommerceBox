# apps/inventory_management/urls.py

from django.urls import path
from .views import (
    # Dashboard
    InventoryDashboardView,
    
    # Categorías
    CategoriaListView,
    CategoriaCreateView,
    CategoriaUpdateView,
    CategoriaDeleteView,
    
    # Marcas
    MarcaListView,
    MarcaCreateView,
    MarcaDetailView,
    MarcaUpdateView,
    MarcaDeleteView,
    MarcaToggleDestacadaView,
    
    # Proveedores
    ProveedorListView,
    ProveedorCreateView,
    ProveedorDetailView,
    ProveedorUpdateView,
    ProveedorDeleteView,
    
    # Productos (Maestro)
    ProductoListView,
    ProductoCreateView,
    ProductoDetailView,
    ProductoUpdateView,
    ProductoDeleteView,
    
    # Quintales
    QuintalListView,
    QuintalCreateView,
    QuintalDetailView,
    QuintalUpdateView,
    QuintalMovimientosView,
    
    # Productos Normales
    ProductoNormalListView,
    ProductoNormalCreateView,
    ProductoNormalDetailView,
    ProductoNormalUpdateView,
    ProductoNormalMovimientosView,
    
    # Búsqueda por código de barras
    BuscarCodigoBarrasView,
    BuscarCodigoAPIView,
    
    # Ajustes de inventario
    AjusteQuintalView,
    AjusteProductoNormalView,
    
    # Compras
    CompraListView,
    CompraCreateView,
    CompraDetailView,
    CompraRecibirView,
    
    # Reportes
    StockCriticoReportView,
    ProximosVencerReportView,
    ValorInventarioReportView,
    TrazabilidadQuintalView,
    ReporteMarcasView,
    
    # APIs JSON
    ProductoBuscarAPIView,
    QuintalesDisponiblesAPIView,
    StockStatusAPIView,
    MarcaBuscarAPIView,
    MarcaDetalleAPIView,
)

app_name = 'inventory_management'

urlpatterns = [
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    path('', InventoryDashboardView.as_view(), name='dashboard'),
    
    # ========================================================================
    # CATEGORÍAS
    # ========================================================================
    path('categorias/', CategoriaListView.as_view(), name='categoria_list'),
    path('categorias/crear/', CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<uuid:pk>/editar/', CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/<uuid:pk>/eliminar/', CategoriaDeleteView.as_view(), name='categoria_delete'),
    
    # ========================================================================
    # MARCAS
    # ========================================================================
    path('marcas/', MarcaListView.as_view(), name='marca_list'),
    path('marcas/crear/', MarcaCreateView.as_view(), name='marca_create'),
    path('marcas/<uuid:pk>/', MarcaDetailView.as_view(), name='marca_detail'),
    path('marcas/<uuid:pk>/editar/', MarcaUpdateView.as_view(), name='marca_update'),
    path('marcas/<uuid:pk>/eliminar/', MarcaDeleteView.as_view(), name='marca_delete'),
    path('marcas/<uuid:pk>/toggle-destacada/', MarcaToggleDestacadaView.as_view(), name='marca_toggle_destacada'),
    
    # ========================================================================
    # PROVEEDORES
    # ========================================================================
    path('proveedores/', ProveedorListView.as_view(), name='proveedor_list'),
    path('proveedores/crear/', ProveedorCreateView.as_view(), name='proveedor_create'),
    path('proveedores/<uuid:pk>/', ProveedorDetailView.as_view(), name='proveedor_detail'),
    path('proveedores/<uuid:pk>/editar/', ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('proveedores/<uuid:pk>/eliminar/', ProveedorDeleteView.as_view(), name='proveedor_delete'),
    
    # ========================================================================
    # PRODUCTOS (MAESTRO)
    # ========================================================================
    path('productos/', ProductoListView.as_view(), name='producto_list'),
    path('productos/crear/', ProductoCreateView.as_view(), name='producto_create'),
    path('productos/<uuid:pk>/', ProductoDetailView.as_view(), name='producto_detail'),
    path('productos/<uuid:pk>/editar/', ProductoUpdateView.as_view(), name='producto_update'),
    path('productos/<uuid:pk>/eliminar/', ProductoDeleteView.as_view(), name='producto_delete'),
    
    # ========================================================================
    # QUINTALES
    # ========================================================================
    path('quintales/', QuintalListView.as_view(), name='quintal_list'),
    path('quintales/crear/', QuintalCreateView.as_view(), name='quintal_create'),
    path('quintales/<uuid:pk>/', QuintalDetailView.as_view(), name='quintal_detail'),
    path('quintales/<uuid:pk>/editar/', QuintalUpdateView.as_view(), name='quintal_update'),
    path('quintales/<uuid:pk>/movimientos/', QuintalMovimientosView.as_view(), name='quintal_movimientos'),
    
    # ========================================================================
    # PRODUCTOS NORMALES
    # ========================================================================
    path('inventario/', ProductoNormalListView.as_view(), name='producto_normal_list'),
    path('inventario/crear/', ProductoNormalCreateView.as_view(), name='producto_normal_create'),
    path('inventario/<uuid:pk>/', ProductoNormalDetailView.as_view(), name='producto_normal_detail'),
    path('inventario/<uuid:pk>/editar/', ProductoNormalUpdateView.as_view(), name='producto_normal_update'),
    path('inventario/<uuid:pk>/movimientos/', ProductoNormalMovimientosView.as_view(), name='producto_normal_movimientos'),
    
    # ========================================================================
    # BÚSQUEDA POR CÓDIGO DE BARRAS
    # ========================================================================
    path('buscar/', BuscarCodigoBarrasView.as_view(), name='buscar_codigo'),
    path('api/buscar-codigo/', BuscarCodigoAPIView.as_view(), name='buscar_codigo_api'),
    
    # ========================================================================
    # AJUSTES DE INVENTARIO
    # ========================================================================
    path('ajustes/quintal/', AjusteQuintalView.as_view(), name='ajuste_quintal'),
    path('ajustes/producto-normal/', AjusteProductoNormalView.as_view(), name='ajuste_producto_normal'),
    
    # ========================================================================
    # COMPRAS
    # ========================================================================
    path('compras/', CompraListView.as_view(), name='compra_list'),
    path('compras/crear/', CompraCreateView.as_view(), name='compra_create'),
    path('compras/<uuid:pk>/', CompraDetailView.as_view(), name='compra_detail'),
    path('compras/<uuid:pk>/recibir/', CompraRecibirView.as_view(), name='compra_recibir'),
    
    # ========================================================================
    # REPORTES
    # ========================================================================
    path('reportes/stock-critico/', StockCriticoReportView.as_view(), name='reporte_stock_critico'),
    path('reportes/proximos-vencer/', ProximosVencerReportView.as_view(), name='reporte_proximos_vencer'),
    path('reportes/valor-inventario/', ValorInventarioReportView.as_view(), name='reporte_valor_inventario'),
    path('reportes/trazabilidad/<uuid:pk>/', TrazabilidadQuintalView.as_view(), name='trazabilidad_quintal'),
    path('reportes/marcas/', ReporteMarcasView.as_view(), name='reporte_marcas'),
    
    # ========================================================================
    # APIs JSON (Para uso con JavaScript/AJAX)
    # ========================================================================
    path('api/productos/buscar/', ProductoBuscarAPIView.as_view(), name='api_producto_buscar'),
    path('api/productos/<uuid:producto_id>/quintales/', QuintalesDisponiblesAPIView.as_view(), name='api_quintales_disponibles'),
    path('api/productos/<uuid:producto_id>/stock/', StockStatusAPIView.as_view(), name='api_stock_status'),
    path('api/marcas/buscar/', MarcaBuscarAPIView.as_view(), name='api_marca_buscar'),
    path('api/marcas/<uuid:pk>/', MarcaDetalleAPIView.as_view(), name='api_marca_detalle'),
]