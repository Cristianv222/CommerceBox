# apps/sales_management/pos/pricing_calculator.py

from decimal import Decimal
from apps.inventory_management.models import Producto, Categoria


class PricingCalculator:
    """
    Servicio para calcular precios, márgenes y descuentos
    """
    
    @staticmethod
    def calcular_precio_venta_producto(producto, margen_porcentaje=None):
        """
        Calcula el precio de venta basado en el costo y margen
        
        Args:
            producto: Producto
            margen_porcentaje: Margen de ganancia (si no se especifica, usa el de la categoría)
        
        Returns:
            Decimal: Precio de venta calculado
        """
        if producto.es_quintal():
            # Para quintales, el precio ya está configurado
            return producto.precio_por_unidad_peso or Decimal('0')
        else:
            # Para productos normales, calcular según margen
            try:
                inventario = producto.inventario_normal
                costo = inventario.costo_unitario
                
                if margen_porcentaje is None:
                    margen_porcentaje = producto.categoria.margen_ganancia_sugerido
                
                precio_venta = costo * (1 + (margen_porcentaje / 100))
                return precio_venta.quantize(Decimal('0.01'))
            except:
                return producto.precio_unitario or Decimal('0')
    
    @staticmethod
    def calcular_utilidad(precio_venta, costo, cantidad=1):
        """
        Calcula la utilidad bruta
        
        Args:
            precio_venta: Precio de venta
            costo: Costo unitario
            cantidad: Cantidad vendida
        
        Returns:
            dict: {'utilidad': Decimal, 'margen_porcentaje': Decimal}
        """
        utilidad = (precio_venta - costo) * cantidad
        
        if precio_venta > 0:
            margen_porcentaje = ((precio_venta - costo) / precio_venta) * 100
        else:
            margen_porcentaje = Decimal('0')
        
        return {
            'utilidad': utilidad.quantize(Decimal('0.01')),
            'margen_porcentaje': margen_porcentaje.quantize(Decimal('0.01'))
        }
    
    @staticmethod
    def validar_descuento(producto, descuento_porcentaje):
        """
        Valida si un descuento es permitido según las reglas de la categoría
        
        Args:
            producto: Producto
            descuento_porcentaje: Descuento solicitado
        
        Returns:
            dict: {'valido': bool, 'mensaje': str}
        """
        descuento_maximo = producto.categoria.descuento_maximo_permitido
        
        if descuento_porcentaje <= descuento_maximo:
            return {
                'valido': True,
                'mensaje': 'Descuento válido'
            }
        else:
            return {
                'valido': False,
                'mensaje': f'El descuento máximo permitido es {descuento_maximo}%'
            }
    
    @staticmethod
    def aplicar_descuento_cliente(precio_base, cliente):
        """
        Aplica el descuento especial del cliente
        
        Args:
            precio_base: Precio base
            cliente: Cliente con descuento
        
        Returns:
            dict: {'precio_final': Decimal, 'descuento_aplicado': Decimal}
        """
        if cliente and cliente.descuento_general > 0:
            descuento = precio_base * (cliente.descuento_general / 100)
            precio_final = precio_base - descuento
            
            return {
                'precio_final': precio_final.quantize(Decimal('0.01')),
                'descuento_aplicado': descuento.quantize(Decimal('0.01'))
            }
        
        return {
            'precio_final': precio_base,
            'descuento_aplicado': Decimal('0')
        }
    
    @staticmethod
    def calcular_impuestos(subtotal, tasa_impuesto=Decimal('0')):
        """
        Calcula impuestos sobre el subtotal
        
        Args:
            subtotal: Subtotal de la venta
            tasa_impuesto: Tasa de impuesto en porcentaje (ej: 12 para 12%)
        
        Returns:
            Decimal: Monto de impuestos
        """
        impuesto = subtotal * (tasa_impuesto / 100)
        return impuesto.quantize(Decimal('0.01'))


# apps/sales_management/pos/discount_manager.py

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class DiscountManager:
    """
    Gestor de descuentos y promociones
    """
    
    @staticmethod
    def calcular_descuento_por_volumen(cantidad, producto):
        """
        Calcula descuento por volumen de compra
        
        Reglas ejemplo:
        - 10-50 unidades: 5%
        - 51-100 unidades: 10%
        - 101+: 15%
        
        Args:
            cantidad: Cantidad comprada
            producto: Producto
        
        Returns:
            Decimal: Porcentaje de descuento
        """
        if producto.es_quintal():
            # Para quintales, basado en peso
            if cantidad >= 100:  # kg
                return Decimal('15')
            elif cantidad >= 50:
                return Decimal('10')
            elif cantidad >= 25:
                return Decimal('5')
        else:
            # Para productos normales, basado en unidades
            if cantidad >= 101:
                return Decimal('15')
            elif cantidad >= 51:
                return Decimal('10')
            elif cantidad >= 10:
                return Decimal('5')
        
        return Decimal('0')
    
    @staticmethod
    def aplicar_promocion_combo(items):
        """
        Aplica descuentos por compra de combos
        Ejemplo: Compra arroz + frijol = 10% descuento en ambos
        
        Args:
            items: Lista de items en el carrito
        
        Returns:
            dict: Descuentos aplicables por item
        """
        # Esta es una implementación básica
        # Puede expandirse con reglas de combos desde BD
        descuentos = {}
        
        # Ejemplo: detectar si hay productos complementarios
        categorias = set()
        for item in items:
            if hasattr(item, 'producto'):
                categorias.add(item.producto.categoria.nombre)
        
        # Si compra de múltiples categorías, dar descuento
        if len(categorias) >= 3:
            for i, item in enumerate(items):
                descuentos[i] = Decimal('5')  # 5% por combo
        
        return descuentos
    
    @staticmethod
    def descuento_cliente_frecuente(cliente):
        """
        Calcula descuento para clientes frecuentes
        
        Args:
            cliente: Cliente
        
        Returns:
            Decimal: Porcentaje de descuento adicional
        """
        if not cliente:
            return Decimal('0')
        
        # Descuento basado en total de compras acumuladas
        if cliente.total_compras >= 10000:
            return Decimal('10')  # Cliente VIP
        elif cliente.total_compras >= 5000:
            return Decimal('7')   # Cliente Gold
        elif cliente.total_compras >= 1000:
            return Decimal('5')   # Cliente Silver
        
        return Decimal('0')
    
    @staticmethod
    def descuento_por_temporada():
        """
        Descuentos por temporada/fecha especial
        
        Returns:
            dict: {'activo': bool, 'porcentaje': Decimal, 'nombre': str}
        """
        hoy = timezone.now().date()
        mes = hoy.month
        dia = hoy.day
        
        # Black Friday (ejemplo: último viernes de noviembre)
        if mes == 11 and dia >= 24:
            return {
                'activo': True,
                'porcentaje': Decimal('20'),
                'nombre': 'Black Friday'
            }
        
        # Navidad
        if mes == 12 and dia <= 25:
            return {
                'activo': True,
                'porcentaje': Decimal('15'),
                'nombre': 'Oferta Navideña'
            }
        
        # Año Nuevo
        if mes == 1 and dia <= 7:
            return {
                'activo': True,
                'porcentaje': Decimal('10'),
                'nombre': 'Inicio de Año'
            }
        
        return {
            'activo': False,
            'porcentaje': Decimal('0'),
            'nombre': ''
        }