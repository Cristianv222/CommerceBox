from decimal import Decimal


class FIFOCalculator:
    """
    Calculador de FIFO (First In, First Out)
    Para determinar qué quintales usar primero en ventas
    """
    
    @staticmethod
    def calcular_distribucion(quintales_ordenados, peso_necesario):
        """
        Calcula cómo distribuir una venta entre múltiples quintales usando FIFO
        
        Args:
            quintales_ordenados (QuerySet): Quintales ordenados por fecha (FIFO)
            peso_necesario (Decimal): Peso total necesario
        
        Returns:
            list: [(quintal, peso_a_tomar), ...]
            None: Si no hay suficiente stock
        """
        distribucion = []
        peso_restante = peso_necesario
        
        for quintal in quintales_ordenados:
            if peso_restante <= 0:
                break
            
            # Tomar lo que se pueda de este quintal
            peso_tomar = min(quintal.peso_actual, peso_restante)
            
            if peso_tomar > 0:
                distribucion.append({
                    'quintal': quintal,
                    'peso_tomar': peso_tomar,
                    'peso_antes': quintal.peso_actual,
                    'peso_despues': quintal.peso_actual - peso_tomar
                })
                
                peso_restante -= peso_tomar
        
        # Si no se pudo cubrir todo el peso
        if peso_restante > 0:
            return None
        
        return distribucion
    
    @staticmethod
    def verificar_disponibilidad_total(quintales_ordenados):
        """
        Calcula el peso total disponible
        
        Args:
            quintales_ordenados (QuerySet): Quintales disponibles
        
        Returns:
            Decimal: Peso total disponible
        """
        return sum(q.peso_actual for q in quintales_ordenados)