from django.core.management.base import BaseCommand
from apps.inventory_management.models import Producto, Quintal
from apps.inventory_management.utils.barcode_generator import BarcodeGenerator


class Command(BaseCommand):
    help = 'Genera códigos de barras para productos sin código'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--regenerar',
            action='store_true',
            help='Regenerar códigos existentes',
        )
    
    def handle(self, *args, **options):
        regenerar = options['regenerar']
        
        self.stdout.write('Generando códigos de barras...\n')
        
        # Productos sin código
        if regenerar:
            productos = Producto.objects.all()
        else:
            productos = Producto.objects.filter(codigo_barras='')
        
        total = productos.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ Todos los productos tienen código'))
            return
        
        generados = 0
        for producto in productos:
            if not producto.codigo_barras or regenerar:
                codigo = BarcodeGenerator.generar_codigo_producto(
                    categoria=producto.categoria,
                    tipo_inventario=producto.tipo_inventario
                )
                producto.codigo_barras = codigo
                producto.save()
                generados += 1
                self.stdout.write(f'  ✓ {producto.nombre}: {codigo}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Generados {generados} códigos'))