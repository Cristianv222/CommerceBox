"""
Configuración de Celery para CommerceBox
"""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Establecer el módulo de configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')

# Crear la instancia de Celery
app = Celery('commercebox')

# Cargar la configuración desde Django settings con el namespace CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubrir tareas en todas las apps instaladas
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de debug para verificar que Celery funciona"""
    print(f'Request: {self.request!r}')