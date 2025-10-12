# apps/notifications/apps.py

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Sistema de Notificaciones'
    
    def ready(self):
        """
        Importar señales cuando la app esté lista
        """
        import apps.notifications.signals  # noqa