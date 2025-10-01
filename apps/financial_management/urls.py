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
    
    # Movimientos
    path('cajas/<uuid:pk>/movimiento/', views.RegistrarMovimientoCajaView.as_view(), name='caja_movimiento'),
    
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
]