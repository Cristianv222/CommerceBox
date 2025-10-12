# apps/stock_alert_system/management/commands/procesar_alertas.py

"""
Comando para procesar alertas del sistema
Ejecutar: python manage.py procesar_alertas
Recomendado en cron cada 30 minutos o 1 hora
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.stock_alert_system.status_calculator import StatusCalculator, AlertaManager
from apps.stock_alert_system.models import ConfiguracionAlerta, Alerta


class Command(BaseCommand):
    help = 'Procesa alertas del sistema de stock - verifica quintales críticos, vencimientos y resuelve alertas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--resolver-automaticas',
            action='store_true',
            help='Resolver alertas automáticamente si el estado mejoró',
        )
        
        parser.add_argument(
            '--limpiar-antiguas',
            type=int,
            default=0,
            help='Días de antigüedad para limpiar alertas resueltas (0 = no limpiar)',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada',
        )
    
    def handle(self, *args, **options):
        verbose = options['verbose']
        
        inicio = timezone.now()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('🚨 PROCESADOR DE ALERTAS - CommerceBox'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # Verificar si las alertas están activas
        config = ConfiguracionAlerta.get_configuracion()
        
        if not config.alertas_activas:
            self.stdout.write(self.style.WARNING('⚠️  Sistema de alertas desactivado en configuración'))
            return
        
        self.stdout.write(f'⏰ Inicio: {inicio.strftime("%d/%m/%Y %H:%M:%S")}\n')
        
        # 1. Verificar quintales individuales críticos
        self.stdout.write('🌾 Verificando quintales críticos...')
        try:
            StatusCalculator.verificar_quintales_individuales()
            alertas_quintales = Alerta.objects.filter(
                tipo_alerta='QUINTAL_CRITICO',
                estado='ACTIVA'
            ).count()
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Completado. Alertas activas de quintales: {alertas_quintales}'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
        
        # 2. Verificar productos próximos a vencer
        self.stdout.write('\n⏰ Verificando productos próximos a vencer...')
        try:
            StatusCalculator.verificar_proximos_vencer()
            alertas_vencimiento = Alerta.objects.filter(
                tipo_alerta='PROXIMO_VENCER',
                estado='ACTIVA'
            ).count()
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Completado. Alertas de vencimiento activas: {alertas_vencimiento}'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
        
        # 3. Resolver alertas automáticamente si se solicita
        if options['resolver_automaticas']:
            self.stdout.write('\n🔄 Resolviendo alertas automáticamente...')
            try:
                AlertaManager.resolver_alertas_automaticamente()
                alertas_resueltas = Alerta.objects.filter(
                    estado='RESUELTA',
                    fecha_resuelta__gte=inicio
                ).count()
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Completado. Alertas resueltas automáticamente: {alertas_resueltas}'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
        
        # 4. Limpiar alertas antiguas si se solicita
        if options['limpiar_antiguas'] > 0:
            dias = options['limpiar_antiguas']
            self.stdout.write(f'\n🧹 Limpiando alertas resueltas con más de {dias} días...')
            try:
                cantidad_eliminada = AlertaManager.limpiar_alertas_antiguas(dias=dias)
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Completado. Alertas eliminadas: {cantidad_eliminada}'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
        
        # Resumen final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE ALERTAS'))
        self.stdout.write('='*60)
        
        # Contar alertas por estado
        alertas_activas = Alerta.objects.filter(estado='ACTIVA').count()
        alertas_urgentes = Alerta.objects.filter(estado='ACTIVA', prioridad='URGENTE').count()
        alertas_altas = Alerta.objects.filter(estado='ACTIVA', prioridad='ALTA').count()
        
        self.stdout.write(f'\n🚨 Alertas ACTIVAS: {alertas_activas}')
        self.stdout.write(f'   - Urgentes: {alertas_urgentes}')
        self.stdout.write(f'   - Prioridad Alta: {alertas_altas}')
        
        # Alertas por tipo
        if verbose:
            self.stdout.write('\n📋 Alertas por tipo:')
            tipos = Alerta.objects.filter(estado='ACTIVA').values('tipo_alerta').distinct()
            for tipo in tipos:
                tipo_alerta = tipo['tipo_alerta']
                cantidad = Alerta.objects.filter(estado='ACTIVA', tipo_alerta=tipo_alerta).count()
                self.stdout.write(f'   - {tipo_alerta}: {cantidad}')
        
        # Tiempo de ejecución
        fin = timezone.now()
        duracion = (fin - inicio).total_seconds()
        
        self.stdout.write(f'\n⏱️  Tiempo de ejecución: {duracion:.2f} segundos')
        self.stdout.write(self.style.SUCCESS('\n✅ Procesamiento completado exitosamente\n'))