from ..models import Producto, Quintal, ProductoNormal
from django.db.models import Q


class BarcodeService:
    """
    Servicio para búsqueda y validación de códigos de barras
    """
    
    @staticmethod
    def buscar_por_codigo(codigo):
        """
        Busca producto o quintal por código de barras
        
        Args:
            codigo (str): Código de barras o código único
        
        Returns:
            dict: {
                'encontrado': bool,
                'tipo': str ('QUINTAL_PRODUCTO', 'QUINTAL_INDIVIDUAL', 'PRODUCTO_NORMAL'),
                'data': object (Producto o Quintal),
                'mensaje': str,
                'puede_vender': bool
            }
        """
        codigo = codigo.strip().upper()
        
        # 1. Buscar si es código de quintal individual (CBX-QNT-...)
        if 'QNT' in codigo:
            try:
                quintal = Quintal.objects.get(codigo_unico=codigo)
                return {
                    'encontrado': True,
                    'tipo': 'QUINTAL_INDIVIDUAL',
                    'data': quintal,
                    'mensaje': f'Quintal encontrado: {quintal.producto.nombre}',
                    'puede_vender': quintal.estado == 'DISPONIBLE' and quintal.peso_actual > 0,
                    'quintal': quintal
                }
            except Quintal.DoesNotExist:
                pass
        
        # 2. Buscar como código de producto
        try:
            producto = Producto.objects.get(codigo_barras=codigo, activo=True)
            
            if producto.es_quintal():
                # Es producto a granel, necesita peso
                quintales_disponibles = Quintal.objects.filter(
                    producto=producto,
                    estado='DISPONIBLE',
                    peso_actual__gt=0
                ).order_by('fecha_recepcion')
                
                return {
                    'encontrado': True,
                    'tipo': 'QUINTAL_PRODUCTO',
                    'data': producto,
                    'mensaje': f'Producto a granel: {producto.nombre}',
                    'puede_vender': quintales_disponibles.exists(),
                    'quintales_disponibles': quintales_disponibles
                }
            else:
                # Es producto normal
                try:
                    inventario = producto.inventario_normal
                    return {
                        'encontrado': True,
                        'tipo': 'PRODUCTO_NORMAL',
                        'data': producto,
                        'mensaje': f'Producto: {producto.nombre}',
                        'puede_vender': inventario.stock_actual > 0,
                        'inventario': inventario
                    }
                except ProductoNormal.DoesNotExist:
                    return {
                        'encontrado': True,
                        'tipo': 'PRODUCTO_NORMAL',
                        'data': producto,
                        'mensaje': f'Producto sin inventario: {producto.nombre}',
                        'puede_vender': False
                    }
        
        except Producto.DoesNotExist:
            pass
        
        # 3. No encontrado
        return {
            'encontrado': False,
            'tipo': None,
            'data': None,
            'mensaje': f'Código no encontrado: {codigo}',
            'puede_vender': False
        }
    
    @staticmethod
    def validar_codigo(codigo):
        """
        Valida formato de código de barras
        
        Args:
            codigo (str): Código a validar
        
        Returns:
            dict: {'valido': bool, 'tipo': str, 'mensaje': str}
        """
        codigo = codigo.strip()
        
        if not codigo:
            return {'valido': False, 'tipo': None, 'mensaje': 'Código vacío'}
        
        # Validar longitud mínima
        if len(codigo) < 5:
            return {'valido': False, 'tipo': None, 'mensaje': 'Código muy corto'}
        
        # Detectar tipo de código
        if codigo.startswith('CBX-PRD-'):
            return {'valido': True, 'tipo': 'PRODUCTO', 'mensaje': 'Código de producto interno'}
        
        if codigo.startswith('CBX-QNT-'):
            return {'valido': True, 'tipo': 'QUINTAL', 'mensaje': 'Código de quintal interno'}
        
        # Códigos numéricos (EAN, UPC, etc.)
        if codigo.isdigit():
            if len(codigo) == 13:
                return {'valido': True, 'tipo': 'EAN13', 'mensaje': 'Código EAN-13'}
            elif len(codigo) == 8:
                return {'valido': True, 'tipo': 'EAN8', 'mensaje': 'Código EAN-8'}
            elif len(codigo) == 12:
                return {'valido': True, 'tipo': 'UPC', 'mensaje': 'Código UPC'}
        
        return {'valido': True, 'tipo': 'OTRO', 'mensaje': 'Código externo'}
    
    @staticmethod
    def buscar_similares(codigo_parcial):
        """
        Busca productos con códigos similares (para autocompletado)
        
        Args:
            codigo_parcial (str): Parte del código
        
        Returns:
            QuerySet de Productos
        """
        return Producto.objects.filter(
            Q(codigo_barras__icontains=codigo_parcial) |
            Q(nombre__icontains=codigo_parcial),
            activo=True
        )[:10]