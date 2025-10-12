# apps/notifications/urls.py

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # TODO: Agregar rutas cuando se implementen las vistas
    path('', views.lista_notificaciones, name='lista'),
    # path('<uuid:id>/', views.detalle_notificacion, name='detalle'),
    path('<uuid:id>/marcar-leida/', views.marcar_leida, name='marcar_leida'),
    # path('preferencias/', views.preferencias, name='preferencias'),
]