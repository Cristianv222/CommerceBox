# apps/reports_analytics/apps.py

from django.apps import AppConfig


class ReportsAnalyticsConfig(AppConfig):
    """
    Configuración de la aplicación Reports & Analytics
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reports_analytics'
    verbose_name = 'Reportes y Análisis'
    
    def ready(self):
        """
        Método que se ejecuta cuando la aplicación está lista
        Aquí se pueden importar señales, registrar tareas, etc.
        """
        # Importar signals si los hay
        try:
            import apps.reports_analytics.signals
        except ImportError:
            pass