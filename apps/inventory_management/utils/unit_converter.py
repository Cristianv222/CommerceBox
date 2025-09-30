from decimal import Decimal


class UnitConverter:
    """
    Conversor de unidades de medida
    """
    
    @staticmethod
    def convertir(cantidad, unidad_origen, unidad_destino):
        """
        Convierte cantidad de una unidad a otra
        
        Args:
            cantidad (Decimal): Cantidad a convertir
            unidad_origen (UnidadMedida): Unidad de origen
            unidad_destino (UnidadMedida): Unidad de destino
        
        Returns:
            Decimal: Cantidad convertida
        """
        if unidad_origen == unidad_destino:
            return cantidad
        
        # Convertir a kilogramos (base)
        cantidad_kg = cantidad * unidad_origen.factor_conversion_kg
        
        # Convertir de kilogramos a unidad destino
        cantidad_destino = cantidad_kg / unidad_destino.factor_conversion_kg
        
        return cantidad_destino
    
    @staticmethod
    def obtener_factor_conversion(unidad_origen, unidad_destino):
        """
        Obtiene el factor de conversión directo
        
        Args:
            unidad_origen (UnidadMedida)
            unidad_destino (UnidadMedida)
        
        Returns:
            Decimal: Factor de conversión
        """
        if unidad_origen == unidad_destino:
            return Decimal('1.0')
        
        return unidad_origen.factor_conversion_kg / unidad_destino.factor_conversion_kg