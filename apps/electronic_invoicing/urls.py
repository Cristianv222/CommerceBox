from django.urls import path
from . import views

app_name = 'electronic_invoicing'

urlpatterns = [
    path('descargar/xml/<uuid:pk>/', views.descargar_xml_sri, name='descargar_xml'),
    path('descargar/pdf/<uuid:pk>/', views.descargar_pdf_sri, name='descargar_pdf'),
    path('ver/xml/<uuid:pk>/', views.ver_xml_sri, name='ver_xml'),
    path('api/xml/<uuid:pk>/', views.api_xml_sri, name='api_xml'),
    path('reenviar-email/<uuid:pk>/', views.reenviar_email_sri, name='reenviar_email'),
    path('reintentar-sri/<uuid:pk>/', views.retry_procesar_factura, name='retry_sri'),
    path('api/punto/actualizar-secuencial/', views.actualizar_secuencial_sri, name='actualizar_secuencial'),
]
