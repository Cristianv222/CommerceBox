from decimal import Decimal
from django.db import transaction
from apps.inventory_management.models import Quintal, MovimientoInventario
from apps.sales_management.models import DetalleVenta

class QuintalSalesService:
    """Servicio para manejar ventas de quintales por peso o dinero"""
    
    @staticmethod
    def calcular_peso_por_dinero(quintal, monto):
        """Calcula cuánto peso corresponde a un monto de dinero"""
        precio_por_unidad = quintal.producto.precio_por_unidad_peso
        if precio_por_unidad and precio_por_unidad > 0:
            return Decimal(str(monto)) / Decimal(str(precio_por_unidad))
        return Decimal('0')
    
    @staticmethod
    def calcular_dinero_por_peso(quintal, peso):
        """Calcula el precio para un peso dado"""
        precio_por_unidad = quintal.producto.precio_por_unidad_peso
        if precio_por_unidad:
            return Decimal(str(peso)) * Decimal(str(precio_por_unidad))
        return Decimal('0')
    
    @classmethod
    @transaction.atomic
    def vender_quintal(cls, quintal, cantidad, tipo_venta='PESO'):
        """
        Vende un quintal por peso o por dinero
        tipo_venta: 'PESO' o 'DINERO'
        cantidad: peso en unidades o monto en dinero
        """
        if tipo_venta == 'DINERO':
            # Convertir dinero a peso
            peso_a_vender = cls.calcular_peso_por_dinero(quintal, cantidad)
            monto_total = Decimal(str(cantidad))
        else:
            # Venta directa por peso
            peso_a_vender = Decimal(str(cantidad))
            monto_total = cls.calcular_dinero_por_peso(quintal, peso_a_vender)
        
        # Validar disponibilidad
        if peso_a_vender > quintal.peso_actual:
            raise ValueError(f'Peso insuficiente. Disponible: {quintal.peso_actual}')
        
        # Actualizar el quintal
        quintal.peso_actual -= peso_a_vender
        if quintal.peso_actual <= 0:
            quintal.estado = 'AGOTADO'
        quintal.save()
        
        return {
            'peso_vendido': peso_a_vender,
            'monto_total': monto_total,
            'quintal': quintal
        }
