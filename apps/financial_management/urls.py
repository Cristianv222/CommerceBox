# apps/financial_management/urls.py

from django.urls import path
from . import views

app_name = 'financial_management'

urlpatterns = [
    # ============================================================================
    # DASHBOARD
    # ============================================================================
    path('', views.FinancialDashboardView.as_view(), name='dashboard'),
    
    # ============================================================================
    # GESTIÓN DE CAJAS
    # ============================================================================
    path('cajas/', views.CajaListView.as_view(), name='caja_list'),
    path('cajas/crear/', views.CajaCreateView.as_view(), name='caja_create'),
    path('cajas/<uuid:pk>/', views.CajaDetailView.as_view(), name='caja_detail'),
    path('cajas/<uuid:pk>/editar/', views.CajaUpdateView.as_view(), name='caja_update'),
    
    # Apertura y Cierre
    path('cajas/<uuid:pk>/abrir/', views.AperturaCajaView.as_view(), name='caja_abrir'),
    path('cajas/<uuid:pk>/cerrar/', views.CierreCajaView.as_view(), name='caja_cerrar'),
    
    # Movimientos - CORREGIDO
    path('cajas/<uuid:pk>/movimiento/', views.RegistrarMovimientoView.as_view(), name='caja_movimiento'),
    
    # ============================================================================
    # ARQUEOS
    # ============================================================================
    path('arqueos/', views.ArqueoListView.as_view(), name='arqueo_list'),
    path('arqueos/<uuid:pk>/', views.ArqueoDetailView.as_view(), name='arqueo_detail'),
    
    # ============================================================================
    # CAJA CHICA
    # ============================================================================
    path('caja-chica/', views.CajaChicaListView.as_view(), name='caja_chica_list'),
    path('caja-chica/crear/', views.CajaChicaCreateView.as_view(), name='caja_chica_create'),
    path('caja-chica/<uuid:pk>/', views.CajaChicaDetailView.as_view(), name='caja_chica_detail'),
    path('caja-chica/<uuid:pk>/editar/', views.CajaChicaUpdateView.as_view(), name='caja_chica_update'),
    
    # Operaciones de Caja Chica
    path('caja-chica/<uuid:pk>/gasto/', views.RegistrarGastoCajaChicaView.as_view(), name='caja_chica_gasto'),
    path('caja-chica/<uuid:pk>/reponer/', views.ReponerCajaChicaView.as_view(), name='caja_chica_reponer'),
    
    # ============================================================================
    # REPORTES
    # ============================================================================
    path('reportes/', views.ReporteFinancieroView.as_view(), name='reporte_financiero'),
    
    # ============================================================================
    # APIs
    # ============================================================================
    path('api/caja/<uuid:pk>/estado/', views.EstadoCajaAPIView.as_view(), name='api_caja_estado'),
    path('api/caja-chica/<uuid:pk>/estado/', views.CajaChicaEstadoAPIView.as_view(), name='api_caja_chica_estado'),

    # ============================================================================
    # CUENTAS POR COBRAR (CRÉDITOS A CLIENTES)
    # ============================================================================
    path('cuentas-por-cobrar/', views.CuentaPorCobrarListView.as_view(), name='cuenta_por_cobrar_list'),
    path('cuentas-por-cobrar/nueva/', views.CuentaPorCobrarCreateView.as_view(), name='cuenta_por_cobrar_create'),
    path('cuentas-por-cobrar/<uuid:pk>/registrar-pago/', views.RegistrarPagoCuentaPorCobrarView.as_view(), name='registrar_pago_cuenta_cobrar'),
    path('cuentas-por-cobrar/<uuid:pk>/cancelar/', views.CancelarCuentaPorCobrarView.as_view(), name='cancelar_cuenta_cobrar'),
    path('reportes/antiguedad-saldos-cobrar/', views.ReporteAntiguedadSaldosCobrarView.as_view(), name='reporte_antiguedad_cobrar'),
    
    # ============================================================================
    # CUENTAS POR PAGAR (DEUDAS CON PROVEEDORES)
    # ============================================================================
    path('cuentas-por-pagar/', views.CuentaPorPagarListView.as_view(), name='cuenta_por_pagar_list'),
    path('cuentas-por-pagar/nueva/', views.CuentaPorPagarCreateView.as_view(), name='cuenta_por_pagar_create'),
    path('cuentas-por-pagar/<uuid:pk>/', views.CuentaPorPagarDetailView.as_view(), name='cuenta_por_pagar_detail'),
    path('cuentas-por-pagar/<uuid:pk>/registrar-pago/', views.RegistrarPagoCuentaPorPagarView.as_view(), name='registrar_pago_cuenta_pagar'),
    path('reportes/antiguedad-saldos-pagar/', views.ReporteAntiguedadSaldosPagarView.as_view(), name='reporte_antiguedad_pagar'),

    # ============================================================================
    # APIs PARA CRÉDITOS
    # ============================================================================
    path('api/credito-cliente/<uuid:cliente_id>/', views.EstadoCreditoClienteAPIView.as_view(), name='api_credito_cliente'),
    path('api/clientes/', views.ClientesAPIView.as_view(), name='api_clientes'),
    path('api/clientes/<uuid:cliente_id>/ventas/', views.ClienteVentasAPIView.as_view(), name='api_cliente_ventas'),
    path('api/cuenta-cobrar/<uuid:cuenta_id>/detalle/', views.CuentaPorCobrarDetalleAPIView.as_view(), name='api_cuenta_cobrar_detalle'),
]