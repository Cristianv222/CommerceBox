import uuid
from django.db import models

class SRIConfig(models.Model):
    """Configuración para la comunicación con APIVendo SRI"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_token = models.CharField(max_length=255, help_text="Token vsr_XXXXX otorgado por APIVendo")
    is_test_mode = models.BooleanField(default=True, help_text="Si está activo, usa el ambiente de pruebas")
    api_url = models.URLField(default="https://apivendo.fronteratech.ec/api/sri/documents/create_and_process_invoice_complete/")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Configuración SRI"
        verbose_name_plural = "Configuraciones SRI"

    def __str__(self):
        return f"Configuración SRI - {'Pruebas' if self.is_test_mode else 'Producción'}"

    @classmethod
    def get_config(cls):
        return cls.objects.filter(is_active=True).first()

class SRILog(models.Model):
    """Log de envíos al SRI"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey('sales_management.Venta', on_delete=models.CASCADE, related_name='sri_logs')
    request_data = models.JSONField()
    response_data = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    invoice_id_apivendo = models.IntegerField(null=True, blank=True)
    invoice_number_sri = models.CharField(max_length=50, blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log SRI"
        verbose_name_plural = "Logs SRI"
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"SRI Log - {self.venta.numero_venta} - {'SUCCESS' if self.success else 'FAILED'}"
