from django.core.management.base import BaseCommand
from django.db import transaction
from apps.inventory_management.models import (
    Categoria, UnidadMedida, Proveedor
)
from decimal import Decimal


class Command(BaseCommand):
    help = 'Configura datos iniciales del inventario'
    
    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write('Configurando datos iniciales del inventario...\n')
        
        # 1. Unidades de medida
        self.stdout.write('Creando unidades de medida...')
        unidades = [
            {'nombre': 'Kilogramo', 'abreviatura': 'kg', 'factor_conversion_kg': Decimal('1.0'), 'es_sistema_metrico': True, 'orden_display': 1},
            {'nombre': 'Gramo', 'abreviatura': 'g', 'factor_conversion_kg': Decimal('0.001'), 'es_sistema_metrico': True, 'orden_display': 2},
            {'nombre': 'Libra', 'abreviatura': 'lb', 'factor_conversion_kg': Decimal('0.453592'), 'es_sistema_metrico': False, 'orden_display': 3},
            {'nombre': 'Onza', 'abreviatura': 'oz', 'factor_conversion_kg': Decimal('0.0283495'), 'es_sistema_metrico': False, 'orden_display': 4},
            {'nombre': 'Quintal', 'abreviatura': 'qq', 'factor_conversion_kg': Decimal('45.3592'), 'es_sistema_metrico': False, 'orden_display': 5},
            {'nombre': 'Arroba', 'abreviatura': '@', 'factor_conversion_kg': Decimal('11.3398'), 'es_sistema_metrico': False, 'orden_display': 6},
        ]
        
        for unidad_data in unidades:
            unidad, created = UnidadMedida.objects.get_or_create(
                abreviatura=unidad_data['abreviatura'],
                defaults=unidad_data
            )
            if created:
                self.stdout.write(f'  ✓ Creada: {unidad.nombre}')
        
        # 2. Categorías
        self.stdout.write('\nCreando categorías...')
        categorias = [
            {'nombre': 'Granos', 'descripcion': 'Arroz, frijol, maíz, etc.', 'margen_ganancia_sugerido': Decimal('35.00'), 'orden': 1},
            {'nombre': 'Enlatados', 'descripcion': 'Productos enlatados y conservas', 'margen_ganancia_sugerido': Decimal('30.00'), 'orden': 2},
            {'nombre': 'Lácteos', 'descripcion': 'Leche, queso, yogurt, etc.', 'margen_ganancia_sugerido': Decimal('25.00'), 'orden': 3},
            {'nombre': 'Limpieza', 'descripcion': 'Productos de limpieza', 'margen_ganancia_sugerido': Decimal('40.00'), 'orden': 4},
            {'nombre': 'Abarrotes', 'descripcion': 'Productos varios de abarrotes', 'margen_ganancia_sugerido': Decimal('30.00'), 'orden': 5},
            {'nombre': 'Bebidas', 'descripcion': 'Bebidas y refrescos', 'margen_ganancia_sugerido': Decimal('35.00'), 'orden': 6},
        ]
        
        for cat_data in categorias:
            categoria, created = Categoria.objects.get_or_create(
                nombre=cat_data['nombre'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'  ✓ Creada: {categoria.nombre}')
        
        # 3. Proveedor de ejemplo
        self.stdout.write('\nCreando proveedor de ejemplo...')
        proveedor_data = {
            'nombre_comercial': 'Distribuidora General',
            'razon_social': 'Distribuidora General S.A.',
            'ruc_nit': '1234567890001',
            'telefono': '+593 99 999 9999',
            'email': 'ventas@distribuidora.com',
            'dias_credito': 30,
            'limite_credito': Decimal('10000.00')
        }
        
        proveedor, created = Proveedor.objects.get_or_create(
            ruc_nit=proveedor_data['ruc_nit'],
            defaults=proveedor_data
        )
        
        if created:
            self.stdout.write(f'  ✓ Creado: {proveedor.nombre_comercial}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Datos iniciales configurados correctamente'))