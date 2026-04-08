"""
ASGI config for commercebox project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Importaciones de enrutamiento de aplicaciones (se añadirán conforme se creen)
from apps.electronic_invoicing import routing as sri_routing

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": get_asgi_application(),

    # WebSocket handler
    "websocket": AuthMiddlewareStack(
        URLRouter(
            sri_routing.websocket_urlpatterns
        )
    ),
})
