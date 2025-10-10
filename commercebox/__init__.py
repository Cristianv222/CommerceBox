"""
Inicialización del módulo commercebox
"""
from __future__ import absolute_import, unicode_literals

# Esto asegurará que la app de Celery siempre se importe cuando Django inicie
from .celery import app as celery_app

__all__ = ('celery_app',)