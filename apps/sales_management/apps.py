# apps/sales_management/apps.py

from django.apps import AppConfig


class SalesManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sales_management'
    verbose_name = 'Gestión de Ventas'
    
    def ready(self):
        """
        Importar señales cuando la app esté lista
        """
        import apps.sales_management.signals