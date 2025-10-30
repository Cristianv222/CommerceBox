# apps/system_configuration/management/commands/system_health_check.py

"""
Comando para realizar health check del sistema CommerceBox
Uso: python manage.py system_health_check
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
import os
import psutil
import time
import logging

from apps.system_configuration.models import HealthCheck

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Realiza health check completo del sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )
    
    def handle(self, *args, **options):
        self.verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('🏥 Iniciando health check del sistema...'))
        
        # Inicializar variables
        errores = []
        advertencias = []
        detalles = {}
        
        # Valores por defecto
        db_ok = False
        db_tiempo = None
        redis_ok = False
        celery_ok = False
        disco_ok = True
        memoria_ok = True
        espacio_libre = 0
        uso_disco_pct = 0
        uso_memoria_pct = 0
        uso_cpu_pct = 0
        
        # 1. Check de base de datos
        self.stdout.write('🗄️ Verificando base de datos...')
        db_ok, db_tiempo, db_error = self._check_database()
        if not db_ok:
            errores.append(f'Base de datos: {db_error}')
        detalles['database'] = {
            'ok': db_ok,
            'tiempo_respuesta_ms': db_tiempo,
            'error': db_error
        }
        
        # 2. Check de Redis
        self.stdout.write('💾 Verificando Redis...')
        redis_ok, redis_error = self._check_redis()
        if not redis_ok:
            advertencias.append(f'Redis: {redis_error}')
        detalles['redis'] = {'ok': redis_ok, 'error': redis_error}
        
        # 3. Check de Celery
        self.stdout.write('⚙️ Verificando Celery...')
        celery_ok, celery_error = self._check_celery()
        if not celery_ok:
            advertencias.append(f'Celery: {celery_error}')
        detalles['celery'] = {'ok': celery_ok, 'error': celery_error}
        
        # 4. Check de disco
        self.stdout.write('💿 Verificando espacio en disco...')
        disco_ok, espacio_libre, uso_disco_pct, disco_error = self._check_disk_space()
        if not disco_ok:
            advertencias.append(f'Disco: {disco_error}')
        detalles['disk'] = {
            'ok': disco_ok,
            'espacio_libre_gb': float(espacio_libre),
            'uso_porcentaje': float(uso_disco_pct),
            'error': disco_error
        }
        
        # 5. Check de memoria
        self.stdout.write('🧠 Verificando memoria RAM...')
        memoria_ok, uso_memoria_pct, memoria_error = self._check_memory()
        if not memoria_ok:
            advertencias.append(f'Memoria: {memoria_error}')
        detalles['memory'] = {
            'ok': memoria_ok,
            'uso_porcentaje': float(uso_memoria_pct),
            'error': memoria_error
        }
        
        # 6. Check de CPU
        self.stdout.write('💻 Verificando CPU...')
        uso_cpu_pct = self._check_cpu()
        detalles['cpu'] = {
            'uso_porcentaje': float(uso_cpu_pct)
        }
        
        # Determinar estado general
        estado_general = 'SALUDABLE'
        if errores:
            estado_general = 'CRITICO'
        elif advertencias:
            estado_general = 'ADVERTENCIA'
        
        # Crear registro de Health Check
        try:
            health_check = HealthCheck.objects.create(
                estado_general=estado_general,
                base_datos_ok=db_ok,
                redis_ok=redis_ok,
                celery_ok=celery_ok,
                disco_ok=disco_ok,
                memoria_ok=memoria_ok,
                tiempo_respuesta_db_ms=db_tiempo,
                espacio_disco_libre_gb=espacio_libre,
                uso_memoria_porcentaje=uso_memoria_pct,
                uso_disco_porcentaje=uso_disco_pct,
                uso_cpu_porcentaje=uso_cpu_pct,
                errores=errores,
                advertencias=advertencias,
                detalles=detalles,
            )
            
            # Mostrar resumen
            self._mostrar_resumen(health_check, errores, advertencias)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error al guardar health check: {str(e)}'))
            logger.error(f"Error al guardar health check: {str(e)}", exc_info=True)
    
    def _check_database(self):
        """Verifica conectividad y rendimiento de la base de datos"""
        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            tiempo = int((time.time() - start) * 1000)  # Convertir a ms
            
            if tiempo > 100:
                return True, tiempo, 'Tiempo de respuesta lento (>100ms)'
            
            return True, tiempo, None
        except Exception as e:
            return False, None, str(e)
    
    def _check_redis(self):
        """Verifica conectividad con Redis"""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            valor = cache.get('health_check')
            if valor == 'ok':
                return True, None
            return False, 'No se pudo leer valor de cache'
        except ImportError:
            return True, 'Redis no configurado (opcional)'
        except Exception as e:
            return False, str(e)
    
    def _check_celery(self):
        """Verifica que Celery esté funcionando"""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                return True, None
            return False, 'No hay workers activos'
        except ImportError:
            return True, 'Celery no configurado (opcional)'
        except Exception as e:
            return False, str(e)
    
    def _check_disk_space(self):
        """Verifica espacio disponible en disco"""
        try:
            disk = psutil.disk_usage('/')
            libre_gb = disk.free / (1024**3)
            porcentaje_usado = disk.percent
            
            if libre_gb < 1:  # Menos de 1 GB libre
                return False, libre_gb, porcentaje_usado, f'Espacio crítico: solo {libre_gb:.2f} GB libres'
            elif porcentaje_usado > 90:
                return False, libre_gb, porcentaje_usado, f'Disco casi lleno: {porcentaje_usado}% usado'
            elif porcentaje_usado > 80:
                return True, libre_gb, porcentaje_usado, f'Espacio limitado: {porcentaje_usado}% usado'
            
            return True, libre_gb, porcentaje_usado, None
        except Exception as e:
            return False, 0, 0, str(e)
    
    def _check_memory(self):
        """Verifica uso de memoria RAM"""
        try:
            memoria = psutil.virtual_memory()
            uso_porcentaje = memoria.percent
            
            if uso_porcentaje > 95:
                return False, uso_porcentaje, f'Memoria crítica: {uso_porcentaje}% usado'
            elif uso_porcentaje > 85:
                return True, uso_porcentaje, f'Memoria alta: {uso_porcentaje}% usado'
            
            return True, uso_porcentaje, None
        except Exception as e:
            return False, 0, str(e)
    
    def _check_cpu(self):
        """Verifica uso de CPU"""
        try:
            # Intervalo de 1 segundo para obtener uso real
            uso_porcentaje = psutil.cpu_percent(interval=1)
            return uso_porcentaje
        except Exception as e:
            logger.warning(f"Error al verificar CPU: {str(e)}")
            return 0
    
    def _mostrar_resumen(self, health_check, errores, advertencias):
        """Muestra resumen del health check"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📊 RESUMEN DE HEALTH CHECK')
        self.stdout.write('='*60)
        
        # Estado general
        estado_colors = {
            'SALUDABLE': self.style.SUCCESS,
            'ADVERTENCIA': self.style.WARNING,
            'CRITICO': self.style.ERROR,
        }
        color_func = estado_colors.get(health_check.estado_general, self.style.SUCCESS)
        self.stdout.write(
            f'\n🎯 Estado General: {color_func(health_check.get_estado_general_display())}\n'
        )
        
        # Componentes
        self.stdout.write('📦 Componentes:')
        componentes = [
            ('Base de Datos', health_check.base_datos_ok, 
             f'{health_check.tiempo_respuesta_db_ms}ms' if health_check.tiempo_respuesta_db_ms else 'N/A'),
            ('Redis', health_check.redis_ok, ''),
            ('Celery', health_check.celery_ok, ''),
            ('Disco', health_check.disco_ok, 
             f'{health_check.espacio_disco_libre_gb:.2f} GB libres ({health_check.uso_disco_porcentaje:.1f}% usado)'),
            ('Memoria', health_check.memoria_ok, 
             f'{health_check.uso_memoria_porcentaje:.1f}% usado'),
            ('CPU', True, 
             f'{health_check.uso_cpu_porcentaje:.1f}% usado'),
        ]
        
        for nombre, estado, info in componentes:
            icono = '✅' if estado else '❌'
            texto = f'  {icono} {nombre}'
            if info:
                texto += f' ({info})'
            
            if estado:
                self.stdout.write(self.style.SUCCESS(texto))
            else:
                self.stdout.write(self.style.ERROR(texto))
        
        # Errores
        if errores:
            self.stdout.write('\n🔴 ERRORES CRÍTICOS:')
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  • {error}'))
        
        # Advertencias
        if advertencias:
            self.stdout.write('\n⚠️ ADVERTENCIAS:')
            for advertencia in advertencias:
                self.stdout.write(self.style.WARNING(f'  • {advertencia}'))
        
        if not errores and not advertencias:
            self.stdout.write(self.style.SUCCESS('\n✅ Todo funciona correctamente!'))
        
        self.stdout.write('\n' + '='*60)