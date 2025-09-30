# apps/financial_management/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Caja(models.Model):
    """Modelo básico de Caja - se implementará completamente después"""
    
    nombre = models.CharField(max_length=100)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('ABIERTA', 'Abierta'),
            ('CERRADA', 'Cerrada'),
        ],
        default='CERRADA'
    )
    fecha_apertura = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    usuario_apertura = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cajas_abiertas',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
    
    def __str__(self):
        return self.nombre