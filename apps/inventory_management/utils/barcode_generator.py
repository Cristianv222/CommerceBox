from datetime import datetime


class BarcodeGenerator:
    """Generador de códigos de barras únicos"""
    
    _contador_producto = 1000
    _contador_quintal = 1000
    
    @classmethod
    def generar_codigo_producto(cls, categoria=None, tipo_inventario='NORMAL'):
        """
        Genera código único para producto
        Formato: CBX-PRD-{TIPO}-{CATEGORIA}-{CONTADOR}
        """
        cls._contador_producto += 1
        tipo_prefix = 'QNT' if tipo_inventario == 'QUINTAL' else 'NRM'
        cat_prefix = categoria.nombre[:3].upper() if categoria else 'GEN'
        return f"CBX-PRD-{tipo_prefix}-{cat_prefix}-{cls._contador_producto:04d}"
    
    @classmethod
    def generar_codigo_quintal(cls, producto=None):
        """
        Genera código único para quintal
        Formato: CBX-QNT-{PRODUCTO}-{FECHA}-{CONTADOR}
        """
        cls._contador_quintal += 1
        timestamp = datetime.now().strftime('%Y%m%d')
        prod_prefix = producto.nombre[:3].upper() if producto else 'GEN'
        return f"CBX-QNT-{prod_prefix}-{timestamp}-{cls._contador_quintal:04d}"