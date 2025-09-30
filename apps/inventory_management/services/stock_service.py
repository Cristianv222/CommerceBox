from decimal import Decimal
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import timedelta
from ..models import Quintal, ProductoNormal, Producto


class StockService:
    """
    Servicio para consultas y análisis de stock
    """
    
    @staticmethod
    def obtener_stock_producto(producto):
        """
        Obtiene información completa de stock de un producto
        
        Args:
            producto: Instancia de Producto
        
        Returns:
            dict con información de stock
        """
        if producto.es_quintal():
            return StockService._stock_quintal(producto)
        else:
            return StockService._stock_normal(producto)
    
    @staticmethod
    def _stock_quintal(producto):
        """Stock de producto tipo QUINTAL"""
        quintales = Quintal.objects.filter(
            producto=producto,
            estado='DISPONIBLE',
            peso_actual__gt=0
        )
        
        peso_total = quintales.aggregate(total=Sum('peso_actual'))['total'] or Decimal('0')
        
        # Quintales críticos (menos del 10%)
        criticos = quintales.filter(
            peso_actual__lte=F('peso_inicial') * 0.1
        ).count()
        
        return {
            'tipo': 'QUINTAL',
            'peso_total_disponible': peso_total,
            'unidad': producto.unidad_medida_base.abreviatura,
            'quintales_disponibles': quintales.count(),
            'quintales_criticos': criticos,
            'tiene_stock': peso_total > 0
        }
    
    @staticmethod
    def _stock_normal(producto):
        """Stock de producto tipo NORMAL"""
        try:
            inventario = producto.inventario_normal
            return {
                'tipo': 'NORMAL',
                'stock_actual': inventario.stock_actual,
                'stock_minimo': inventario.stock_minimo,
                'stock_maximo': inventario.stock_maximo,
                'estado': inventario.estado_stock(),
                'necesita_reorden': inventario.necesita_reorden(),
                'valor_inventario': inventario.valor_inventario(),
                'tiene_stock': inventario.stock_actual > 0
            }
        except ProductoNormal.DoesNotExist:
            return {
                'tipo': 'NORMAL',
                'stock_actual': 0,
                'estado': 'AGOTADO',
                'tiene_stock': False
            }
    
    @staticmethod
    def obtener_productos_criticos():
        """
        Obtiene todos los productos con stock crítico
        
        Returns:
            dict con listas de productos críticos
        """
        # Quintales críticos
        quintales_criticos = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__lte=F('peso_inicial') * 0.1,
            peso_actual__gt=0
        ).select_related('producto', 'proveedor')
        
        # Productos normales críticos
        productos_criticos = ProductoNormal.objects.filter(
            stock_actual__lte=F('stock_minimo'),
            stock_actual__gt=0
        ).select_related('producto')
        
        # Productos agotados
        agotados = ProductoNormal.objects.filter(
            stock_actual=0
        ).select_related('producto')
        
        return {
            'quintales_criticos': list(quintales_criticos),
            'productos_normales_criticos': list(productos_criticos),
            'productos_agotados': list(agotados),
            'total_alertas': quintales_criticos.count() + productos_criticos.count() + agotados.count()
        }
    
    @staticmethod
    def obtener_proximos_vencer(dias=7):
        """
        Obtiene quintales próximos a vencer
        
        Args:
            dias: Días hacia adelante para buscar
        
        Returns:
            QuerySet de Quintales
        """
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=dias)
        
        return Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=hoy
        ).select_related('producto', 'proveedor').order_by('fecha_vencimiento')
    
    @staticmethod
    def calcular_valor_inventario():
        """
        Calcula el valor total del inventario
        
        Returns:
            dict con valores desglosados
        """
        # Valor quintales
        valor_quintales = Quintal.objects.filter(
            estado='DISPONIBLE'
        ).aggregate(
            total=Sum(F('peso_actual') * F('costo_por_unidad'))
        )['total'] or Decimal('0')
        
        # Valor productos normales
        valor_normales = ProductoNormal.objects.aggregate(
            total=Sum(F('stock_actual') * F('costo_unitario'))
        )['total'] or Decimal('0')
        
        return {
            'valor_quintales': valor_quintales,
            'valor_productos_normales': valor_normales,
            'valor_total': valor_quintales + valor_normales
        }
    
    @staticmethod
    def obtener_quintales_fifo(producto, peso_necesario):
        """
        Obtiene quintales según método FIFO para cubrir peso necesario
        
        Args:
            producto: Instancia de Producto
            peso_necesario: Decimal - peso total necesario
        
        Returns:
            list: Lista de tuplas (quintal, peso_a_tomar)
        """
        quintales_disponibles = Quintal.objects.filter(
            producto=producto,
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).order_by('fecha_recepcion')  # FIFO: Más antiguo primero
        
        resultado = []
        peso_restante = peso_necesario
        
        for quintal in quintales_disponibles:
            if peso_restante <= 0:
                break
            
            peso_tomar = min(quintal.peso_actual, peso_restante)
            resultado.append((quintal, peso_tomar))
            peso_restante -= peso_tomar
        
        if peso_restante > 0:
            # No hay suficiente stock
            return None
        
        return resultado