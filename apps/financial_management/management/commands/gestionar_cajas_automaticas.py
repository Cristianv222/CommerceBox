# apps/financial_management/management/commands/gestionar_cajas_automaticas.py

"""
Comando de Django para gestión automática de cajas
Puede ejecutarse manualmente o vía cron/celery
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.financial_management.cash_management.auto_cash_service import AutoCashService


class Command(BaseCommand):
    help = 'Gestiona automáticamente las cajas (reportes, verificación)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reporte',
            action='store_true',
            help='Muestra reporte de cajas abiertas',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Gestión Automática de Cajas ===\n'))
        
        if options['reporte']:
            self.mostrar_reporte()
        else:
            self.mostrar_reporte()
    
    def mostrar_reporte(self):
        """Muestra reporte de cajas abiertas"""
        from apps.financial_management.models import Caja
        
        cajas_abiertas = Caja.objects.filter(estado='ABIERTA')
        
        self.stdout.write(f'\n📊 Cajas actualmente abiertas: {cajas_abiertas.count()}\n')
        
        if cajas_abiertas.count() == 0:
            self.stdout.write(self.style.WARNING('  No hay cajas abiertas\n'))
            return
        
        for caja in cajas_abiertas:
            tiempo_abierta = timezone.now() - caja.fecha_apertura
            dias = tiempo_abierta.days
            horas = tiempo_abierta.seconds // 3600
            
            self.stdout.write(
                f'  • {caja.nombre} ({caja.codigo})\n'
                f'    Usuario: {caja.usuario_apertura.username}\n'
                f'    Abierta hace: {dias} días, {horas} horas\n'
                f'    Monto actual: ${caja.monto_actual}\n'
            )
