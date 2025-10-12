# apps/stock_alert_system/management/commands/recalcular_stock.py

"""
Comando para recalcular estados de stock de todos los productos
Ejecutar: python manage.py recalcular_stock
Útil después de: importaciones, migraciones, mantenimiento
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from apps.stock_alert_system.status_calculator import StatusCalculator
from apps.stock_alert_system.models import EstadoStock, get_estadisticas_globales
from apps.inventory_management.models import Producto


class Command(BaseCommand):
    help = 'Recalcula estados de stock para todos los productos del sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--producto-id',
            type=str,
            help='UUID del producto específico a recalcular',
        )
        
        parser.add_argument(
            '--tipo',
            type=str,
            choices=['QUINTAL', 'NORMAL'],
            help='Recalcular solo productos de este tipo',
        )
        
        parser.add_argument(
            '--solo-criticos',
            action='store_true',
            help='Recalcular solo productos en estado CRÍTICO o AGOTADO',
        )
        
        parser.add_argument(
            '--crear-faltantes',
            action='store_true',
            help='Crear EstadoStock para productos que no lo tengan',
        )
        
        parser.add_argument(
            '--estadisticas',
            action='store_true',
            help='Mostrar estadísticas detalladas al final',
        )
    
    def handle(self, *args, **options):
        inicio = timezone.now()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('♻️  RECALCULADOR DE ESTADOS DE STOCK - CommerceBox'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        self.stdout.write(f'⏰ Inicio: {inicio.strftime("%d/%m/%Y %H:%M:%S")}\n')
        
        # Crear estados faltantes si se solicita
        if options['crear_faltantes']:
            self.stdout.write('🔧 Creando estados de stock faltantes...')
            self._crear_estados_faltantes()
        
        # Determinar qué productos procesar
        productos = self._obtener_productos(options)
        
        if not productos.exists():
            self.stdout.write(self.style.WARNING('⚠️  No se encontraron productos para procesar'))
            return
        
        total = productos.count()
        self.stdout.write(f'\n📦 Productos a procesar: {total}\n')
        
        # Procesar productos
        procesados = 0
        errores = 0
        cambios_estado = []
        
        self.stdout.write('🔄 Procesando...\n')
        
        for i, producto in enumerate(productos, 1):
            try:
                # Obtener estado anterior si existe
                try:
                    estado_anterior = EstadoStock.objects.get(producto=producto).estado_semaforo
                except EstadoStock.DoesNotExist:
                    estado_anterior = None
                
                # Recalcular estado
                estado_nuevo = StatusCalculator.calcular_estado(producto)
                
                # Verificar si cambió
                if estado_anterior and estado_anterior != estado_nuevo.estado_semaforo:
                    cambios_estado.append({
                        'producto': producto.nombre,
                        'anterior': estado_anterior,
                        'nuevo': estado_nuevo.estado_semaforo
                    })
                
                procesados += 1
                
                # Mostrar progreso cada 10 productos
                if i % 10 == 0 or i == total:
                    porcentaje = (i / total) * 100
                    self.stdout.write(
                        f'   Progreso: {i}/{total} ({porcentaje:.1f}%) - '
                        f'Procesados: {procesados}, Errores: {errores}',
                        ending='\r'
                    )
            
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'\n   ❌ Error en {producto.nombre}: {str(e)}')
                )
        
        # Nueva línea después del progreso
        self.stdout.write('')
        
        # Mostrar cambios de estado
        if cambios_estado:
            self.stdout.write(self.style.WARNING(f'\n🔄 Cambios de estado detectados: {len(cambios_estado)}'))
            for cambio in cambios_estado[:10]:  # Mostrar solo los primeros 10
                self.stdout.write(
                    f"   • {cambio['producto']}: "
                    f"{cambio['anterior']} → {cambio['nuevo']}"
                )
            
            if len(cambios_estado) > 10:
                self.stdout.write(f'   ... y {len(cambios_estado) - 10} más')
        
        # Estadísticas finales
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DEL PROCESO'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'\n✅ Productos procesados: {procesados}')
        self.stdout.write(f'❌ Errores: {errores}')
        self.stdout.write(f'🔄 Cambios de estado: {len(cambios_estado)}')
        
        # Estadísticas detalladas si se solicita
        if options['estadisticas']:
            self._mostrar_estadisticas()
        
        # Tiempo de ejecución
        fin = timezone.now()
        duracion = (fin - inicio).total_seconds()
        
        self.stdout.write(f'\n⏱️  Tiempo de ejecución: {duracion:.2f} segundos')
        
        if errores == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ Recálculo completado exitosamente\n'))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  Recálculo completado con {errores} error(es)\n'
            ))
    
    def _obtener_productos(self, options):
        """Determina qué productos procesar según las opciones"""
        # Si se especifica un producto específico
        if options['producto_id']:
            try:
                producto = Producto.objects.get(id=options['producto_id'], activo=True)
                return Producto.objects.filter(id=producto.id)
            except Producto.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'❌ Producto con ID {options["producto_id"]} no encontrado'
                ))
                return Producto.objects.none()
        
        # Base: productos activos
        productos = Producto.objects.filter(activo=True)
        
        # Filtrar por tipo si se especifica
        if options['tipo']:
            productos = productos.filter(tipo_inventario=options['tipo'])
        
        # Filtrar solo críticos si se solicita
        if options['solo_criticos']:
            productos = productos.filter(
                Q(estado_stock__estado_semaforo='CRITICO') |
                Q(estado_stock__estado_semaforo='AGOTADO')
            )
        
        return productos.order_by('nombre')
    
    def _crear_estados_faltantes(self):
        """Crea EstadoStock para productos que no lo tengan"""
        productos_sin_estado = Producto.objects.filter(
            activo=True,
            estado_stock__isnull=True
        )
        
        creados = 0
        for producto in productos_sin_estado:
            EstadoStock.objects.create(
                producto=producto,
                tipo_inventario=producto.tipo_inventario,
                estado_semaforo='NORMAL'
            )
            creados += 1
        
        if creados > 0:
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Creados {creados} estados de stock nuevos\n'
            ))
        else:
            self.stdout.write('   ℹ️  Todos los productos ya tienen estado de stock\n')
    
    def _mostrar_estadisticas(self):
        """Muestra estadísticas detalladas del sistema"""
        stats = get_estadisticas_globales()
        
        self.stdout.write('\n📈 ESTADÍSTICAS GLOBALES DEL SISTEMA')
        self.stdout.write('-' * 60)
        
        self.stdout.write(f'\nTotal de productos: {stats["total_productos"]}')
        
        self.stdout.write('\n🟢 Productos NORMALES: {} ({:.1f}%)'.format(
            stats['productos_normales'],
            stats['porcentaje_normales']
        ))
        
        self.stdout.write('🟡 Productos BAJOS: {} ({:.1f}%)'.format(
            stats['productos_bajos'],
            stats['porcentaje_bajos']
        ))
        
        self.stdout.write('🔴 Productos CRÍTICOS: {} ({:.1f}%)'.format(
            stats['productos_criticos'],
            stats['porcentaje_criticos']
        ))
        
        self.stdout.write('⚫ Productos AGOTADOS: {} ({:.1f}%)'.format(
            stats['productos_agotados'],
            stats['porcentaje_agotados']
        ))
        
        self.stdout.write(f'\n🚨 Alertas activas: {stats["alertas_activas"]}')
        self.stdout.write(f'   - Alertas urgentes: {stats["alertas_urgentes"]}')
        
        # Estados por tipo de inventario
        quintales_estados = EstadoStock.objects.filter(tipo_inventario='QUINTAL')
        normales_estados = EstadoStock.objects.filter(tipo_inventario='NORMAL')
        
        self.stdout.write(f'\n📦 Por tipo de inventario:')
        self.stdout.write(f'   - Quintales: {quintales_estados.count()}')
        self.stdout.write(f'   - Productos Normales: {normales_estados.count()}')