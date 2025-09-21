"""
CommerceBox - Comando de configuración inicial
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.inventory_management.models import (
    ConfiguracionInventario, Categoria, Proveedor, Marca
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Configuración inicial de CommerceBox'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reiniciar configuración existente',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando configuración de CommerceBox...')
        )
        
        try:
            with transaction.atomic():
                # Crear usuario administrador
                self._crear_admin()
                
                # Crear configuración inicial
                self._crear_configuracion()
                
                # Crear categorías por defecto
                self._crear_categorias()
                
                # Crear marcas por defecto
                self._crear_marcas()
                
                # Crear proveedor por defecto
                self._crear_proveedor()
                
                self.stdout.write(
                    self.style.SUCCESS('🎉 CommerceBox configurado exitosamente!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en configuración: {str(e)}')
            )
            raise

    def _crear_admin(self):
        """Crear usuario administrador si no existe"""
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@commercebox.com',
                password='admin123',
                first_name='Administrador',
                last_name='CommerceBox'
            )
            self.stdout.write('✅ Usuario administrador creado')
        else:
            self.stdout.write('ℹ️ Usuario administrador ya existe')

    def _crear_configuracion(self):
        """Crear configuración inicial"""
        admin_user = User.objects.get(username='admin')
        
        config, created = ConfiguracionInventario.objects.get_or_create(
            defaults={
                'prefijo_codigo_quintal': 'CBX-QNT',
                'prefijo_codigo_producto': 'CBX-PRD',
                'dias_vencimiento_alerta': 30,
                'porcentaje_stock_bajo': 20,
                'porcentaje_stock_critico': 10,
                'unidades_peso_disponibles': ['kg', 'lb', 'arroba', 'quintal'],
                'creado_por': admin_user
            }
        )
        
        if created:
            self.stdout.write('✅ Configuración inicial creada')
        else:
            self.stdout.write('ℹ️ Configuración ya existe')

    def _crear_categorias(self):
        """Crear categorías por defecto"""
        categorias_default = [
            ('ALM', 'Alimentos', 'Productos alimenticios', 25.0),
            ('BEB', 'Bebidas', 'Bebidas y refrescos', 30.0),
            ('LIM', 'Limpieza', 'Productos de limpieza', 35.0),
            ('MED', 'Medicinas', 'Productos farmacéuticos', 40.0),
            ('ACC', 'Accesorios', 'Accesorios varios', 50.0),
        ]
        
        admin_user = User.objects.get(username='admin')
        
        for codigo, nombre, descripcion, margen in categorias_default:
            categoria, created = Categoria.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'margen_ganancia': margen,
                    'descuento_maximo': 10.0,
                    'creado_por': admin_user
                }
            )
            if created:
                self.stdout.write(f'✅ Categoría {nombre} creada')

    def _crear_marcas(self):
        """Crear marcas por defecto"""
        marcas_default = [
            ('GEN', 'Genérica', 'Marca genérica', 'Local'),
            ('NAC', 'Nacional', 'Marca nacional', 'Nacional'),
            ('IMP', 'Importada', 'Marca importada', 'Internacional'),
        ]
        
        admin_user = User.objects.get(username='admin')
        
        for codigo, nombre, fabricante, pais in marcas_default:
            marca, created = Marca.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'fabricante': fabricante,
                    'pais_origen': pais,
                    'creado_por': admin_user
                }
            )
            if created:
                self.stdout.write(f'✅ Marca {nombre} creada')

    def _crear_proveedor(self):
        """Crear proveedor por defecto"""
        admin_user = User.objects.get(username='admin')
        
        proveedor, created = Proveedor.objects.get_or_create(
            codigo='PROV001',
            defaults={
                'nombre': 'Proveedor General',
                'razon_social': 'Proveedor General S.A.',
                'ruc': '000000000001',
                'telefono': '000-000-0000',
                'email': 'proveedor@ejemplo.com',
                'direccion': 'Dirección del proveedor',
                'limite_credito': 10000.00,
                'dias_credito': 30,
                'creado_por': admin_user
            }
        )
        
        if created:
            self.stdout.write('✅ Proveedor general creado')
        else:
            self.stdout.write('ℹ️ Proveedor general ya existe')