from django.core.exceptions import ValidationError
from decimal import Decimal


class InventoryValidators:
    """Validadores personalizados para inventario"""
    
    @staticmethod
    def validar_peso_positivo(peso):
        """Valida que el peso sea positivo"""
        if peso <= 0:
            raise ValidationError("El peso debe ser mayor a cero")
        return peso
    
    @staticmethod
    def validar_stock_suficiente(stock_actual, cantidad_solicitada):
        """Valida que haya suficiente stock"""
        if stock_actual < cantidad_solicitada:
            raise ValidationError(
                f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {cantidad_solicitada}"
            )
        return True
    
    @staticmethod
    def validar_codigo_barras(codigo):
        """Valida formato de código de barras"""
        if not codigo or len(codigo) < 5:
            raise ValidationError("Código de barras inválido")
        return codigo.strip().upper()
    
    @staticmethod
    def validar_costo_positivo(costo):
        """Valida que el costo sea positivo"""
        if costo <= 0:
            raise ValidationError("El costo debe ser mayor a cero")
        return costo