"""
URLs del frontend - Páginas HTML con Django Templates
"""

from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_home'),
    
    # Inventario
    path('inventario/', views.inventario_view, name='inventario'),
    
    # Ventas
    path('ventas/', views.ventas_view, name='ventas'),
    path('ventas/nueva/', views.ventas_view, name='ventas_nueva'),
    
    # Reportes
    path('reportes/', views.reportes_view, name='reportes'),
    
    # Perfil
    path('perfil/', views.perfil_view, name='perfil'),
]