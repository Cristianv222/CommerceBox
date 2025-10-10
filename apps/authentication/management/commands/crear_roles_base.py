from django.core.management.base import BaseCommand
from apps.authentication.models import Rol


class Command(BaseCommand):
    help = 'Crea los roles base del sistema'

    def handle(self, *args, **options):
        roles_base = [
            {
                'nombre': 'Administrador',
                'codigo': 'ADMIN',
                'descripcion': 'Acceso total al sistema',
                'permissions': ['*']
            },
            {
                'nombre': 'Supervisor',
                'codigo': 'SUPERVISOR',
                'descripcion': 'Supervisor con acceso a reportes y gestión',
                'permissions': [
                    'inventory.view', 'inventory.add', 'inventory.change',
                    'sales.view', 'sales.add', 'sales.change',
                    'financial.view', 'reports.view', 'notifications.view'
                ]
            },
            {
                'nombre': 'Vendedor',
                'codigo': 'VENDEDOR',
                'descripcion': 'Personal de ventas',
                'permissions': ['inventory.view', 'sales.view', 'sales.add']
            },
            {
                'nombre': 'Cajero',
                'codigo': 'CAJERO',
                'descripcion': 'Personal de caja',
                'permissions': ['sales.view', 'financial.view', 'financial.add']
            },
        ]
        
        for rol_data in roles_base:
            rol, created = Rol.objects.get_or_create(
                codigo=rol_data['codigo'],
                defaults={
                    'nombre': rol_data['nombre'],
                    'descripcion': rol_data['descripcion'],
                    'permissions': rol_data['permissions'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Rol creado: {rol.nombre}'))
            else:
                self.stdout.write(f'- Rol ya existe: {rol.nombre}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Roles base creados correctamente'))