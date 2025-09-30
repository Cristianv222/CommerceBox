from django.core.management.base import BaseCommand
from apps.inventory_management.models import Quintal, ProductoNormal, MovimientoQuintal
from decimal import Decimal


class Command(BaseCommand):
    help = 'Valida la integridad de los datos del inventario'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Validando integridad del inventario...\n')
        
        errores = 0
        advertencias = 0
        
        # 1. Validar quintales
        self.stdout.write('Validando quintales...')
        quintales = Quintal.objects.all()
        
        for quintal in quintales:
            # Peso actual no puede ser mayor que peso inicial
            if quintal.peso_actual > quintal.peso_inicial:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ ERROR: Quintal {quintal.codigo_unico} tiene peso_actual > peso_inicial'
                ))
                errores += 1
            
            # Peso actual negativo
            if quintal.peso_actual < 0:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ ERROR: Quintal {quintal.codigo_unico} tiene peso negativo'
                ))
                errores += 1
            
            # Estado inconsistente
            if quintal.peso_actual == 0 and quintal.estado != 'AGOTADO':
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ ADVERTENCIA: Quintal {quintal.codigo_unico} tiene peso 0 pero no está AGOTADO'
                ))
                advertencias += 1
        
        # 2. Validar productos normales
        self.stdout.write('\nValidando productos normales...')
        productos_normales = ProductoNormal.objects.all()
        
        for producto in productos_normales:
            # Stock negativo
            if producto.stock_actual < 0:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ ERROR: {producto.producto.nombre} tiene stock negativo'
                ))
                errores += 1
            
            # Stock mayor que máximo
            if producto.stock_maximo and producto.stock_actual > producto.stock_maximo:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ ADVERTENCIA: {producto.producto.nombre} excede stock máximo'
                ))
                advertencias += 1
        
        # 3. Validar movimientos
        self.stdout.write('\nValidando movimientos...')
        movimientos = MovimientoQuintal.objects.all()
        
        for mov in movimientos:
            # Peso antes y después deben ser consistentes
            diferencia_esperada = mov.peso_antes + mov.peso_movimiento
            if abs(diferencia_esperada - mov.peso_despues) > Decimal('0.001'):
                self.stdout.write(self.style.ERROR(
                    f'  ✗ ERROR: Movimiento inconsistente en quintal {mov.quintal.codigo_unico}'
                ))
                errores += 1
        
        # Resumen
        self.stdout.write('\n' + '='*50)
        if errores == 0 and advertencias == 0:
            self.stdout.write(self.style.SUCCESS('✅ Integridad verificada: Sin errores ni advertencias'))
        else:
            if errores > 0:
                self.stdout.write(self.style.ERROR(f'❌ Errores encontrados: {errores}'))
            if advertencias > 0:
                self.stdout.write(self.style.WARNING(f'⚠️ Advertencias: {advertencias}'))