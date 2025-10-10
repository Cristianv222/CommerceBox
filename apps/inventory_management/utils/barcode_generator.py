"""
Generador de códigos de barras cortos
"""
import random
import string
from django.db import transaction


class BarcodeGenerator:
    """
    Generador de códigos de barras únicos y cortos
    Formato: 3 LETRAS + 5 NÚMEROS (ej: ABC12345)
    """
    
    @staticmethod
    def generar_codigo_producto(categoria=None, tipo_inventario='NORMAL'):
        """
        Genera código único para producto
        Formato: XXX12345 (3 letras + 5 números)
        
        Returns:
            str: Código único de 8 caracteres
        """
        from apps.inventory_management.models import Producto
        
        max_intentos = 100
        for _ in range(max_intentos):
            # 3 letras aleatorias
            letras = ''.join(random.choices(string.ascii_uppercase, k=3))
            # 5 números aleatorios
            numeros = ''.join(random.choices(string.digits, k=5))
            # Combinar
            codigo = f"{letras}{numeros}"
            
            # Verificar que no exista
            if not Producto.objects.filter(codigo_barras=codigo).exists():
                return codigo
        
        raise Exception("No se pudo generar código único después de 100 intentos")
    
    @staticmethod
    def generar_codigo_quintal(producto=None):
        """
        Genera código único para quintal
        Formato: QXX12345 (Q + 2 letras + 5 números)
        
        Args:
            producto: Instancia del producto
        
        Returns:
            str: Código único de 8 caracteres empezando con Q
        """
        from apps.inventory_management.models import Quintal
        
        max_intentos = 100
        for _ in range(max_intentos):
            # Q + 2 letras aleatorias + 5 números
            letras = ''.join(random.choices(string.ascii_uppercase, k=2))
            numeros = ''.join(random.choices(string.digits, k=5))
            codigo = f"Q{letras}{numeros}"
            
            # Verificar que no exista
            if not Quintal.objects.filter(codigo_unico=codigo).exists():
                return codigo
        
        raise Exception("No se pudo generar código de quintal único")
    
    @staticmethod
    def validar_codigo(codigo):
        """
        Valida que el código tenga el formato correcto
        
        Args:
            codigo (str): Código a validar
        
        Returns:
            bool: True si es válido
        """
        if not codigo or len(codigo) != 8:
            return False
        
        # Para quintales: Q + 2 letras + 5 números
        if codigo.startswith('Q'):
            return (codigo[0] == 'Q' and 
                   codigo[1:3].isalpha() and 
                   codigo[3:].isdigit())
        
        # Para productos: 3 letras + 5 números
        return codigo[:3].isalpha() and codigo[3:].isdigit()
