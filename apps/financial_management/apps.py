# apps/financial_management/apps.py

from django.apps import AppConfig


class FinancialManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.financial_management'
    verbose_name = 'Gestión Financiera'
    
    def ready(self):
        """
        Importar signals cuando la app esté lista
        """
        # Importar signals para que se registren
        import apps.financial_management.signals