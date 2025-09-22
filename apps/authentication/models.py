from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado para CommerceBox
    """
    telefono = models.CharField(max_length=20, blank=True, null=True)
    cedula = models.CharField(max_length=20, unique=True, blank=True, null=True)
    cargo = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        
    def __str__(self):
        return f"{self.username} - {self.first_name} {self.last_name}"