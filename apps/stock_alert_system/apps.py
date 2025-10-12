# apps/stock_alert_system/apps.py

from django.apps import AppConfig


class StockAlertSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stock_alert_system'
    verbose_name = 'Sistema de Alertas de Stock'
    
    def ready(self):
        """
        Se ejecuta cuando la app está lista
        Aquí importamos las señales para que se registren
        """
        # Importar signals para que se registren
        import apps.stock_alert_system.signals
        
        # Mensaje de inicio
        print("🚨 Sistema de Alertas de Stock cargado correctamente")