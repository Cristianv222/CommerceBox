from django.urls import path
from . import views

app_name = 'sri'

urlpatterns = [
    path('dashboard/', views.SriDashboardView.as_view(), name='dashboard'),
    path('test-send/', views.SriTestSendView.as_view(), name='test_send'),
    path('config/update/', views.SriConfigUpdateView.as_view(), name='config_update'),
    path('retry/<uuid:pk>/', views.SriRetryView.as_view(), name='retry'),
]
