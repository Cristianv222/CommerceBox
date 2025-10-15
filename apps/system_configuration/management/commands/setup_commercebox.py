# apps/system_configuration/management/commands/setup_commercebox_complete.py

"""
CommerceBox - Comando de Configuración Inicial COMPLETA
Unifica la configuración del sistema + configuración operativa
Versión: 2.0 - Unificado
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

# Importaciones de system_configuration
from apps.system_configuration.models import (
    ConfiguracionSistema, ParametroSistema
)

# Importaciones de inventory_management
from apps.inventory_management.models import (
    ConfiguracionInventario, Categoria, Proveedor, Marca
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Configuración inicial COMPLETA de CommerceBox (Sistema + Operativo)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reiniciar configuración existente (¡CUIDADO!)',
        )
        parser.add_argument(
            '--skip-admin',
            action='store_true',
            help='Saltar creación de usuario administrador',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Contraseña para usuario administrador (default: admin123)',
        )

    def handle(self, *args, **options):
        self.reset = options['reset']
        self.skip_admin = options['skip_admin']
        self.admin_password = options['admin_password']
        
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('🚀 CONFIGURACIÓN INICIAL COMPLETA DE COMMERCEBOX')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')
        
        if self.reset:
            self.stdout.write(
                self.style.WARNING('⚠️  MODO RESET ACTIVADO - Se eliminarán datos existentes')
            )
            confirmar = input('¿Está seguro? (escriba "SI" para confirmar): ')
            if confirmar != 'SI':
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return
        
        try:
            with transaction.atomic():
                # PARTE 1: CONFIGURACIÓN DEL SISTEMA
                self.stdout.write('\n' + '▶' * 35)
                self.stdout.write(
                    self.style.SUCCESS('📦 PARTE 1: CONFIGURACIÓN DEL SISTEMA')
                )
                self.stdout.write('▶' * 35 + '\n')
                
                self._configurar_sistema()
                self._crear_parametros_sistema()
                
                # PARTE 2: CONFIGURACIÓN OPERATIVA
                self.stdout.write('\n' + '▶' * 35)
                self.stdout.write(
                    self.style.SUCCESS('📦 PARTE 2: CONFIGURACIÓN OPERATIVA')
                )
                self.stdout.write('▶' * 35 + '\n')
                
                if not self.skip_admin:
                    self._crear_usuario_admin()
                
                self._configurar_inventario()
                self._crear_categorias()
                self._crear_marcas()
                self._crear_proveedor()
                
                # RESUMEN FINAL
                self._mostrar_resumen()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error en configuración: {str(e)}')
            )
            import traceback
            traceback.print_exc()
            raise

    # ========================================================================
    # PARTE 1: CONFIGURACIÓN DEL SISTEMA
    # ========================================================================

    def _configurar_sistema(self):
        """Crear ConfiguracionSistema (Singleton)"""
        self.stdout.write('📋 Configurando sistema global...')
        
        if self.reset:
            ConfiguracionSistema.objects.all().delete()
        
        config, created = ConfiguracionSistema.objects.get_or_create(pk=1)
        
        if created:
            self.stdout.write(self.style.SUCCESS('  ✅ ConfiguracionSistema creada'))
            self.config_sistema_creada = True
        else:
            self.stdout.write(self.style.WARNING('  ℹ️  ConfiguracionSistema ya existe'))
            self.config_sistema_creada = False
        
        self.config_sistema = config

    def _crear_parametros_sistema(self):
        """Crear parámetros del sistema por módulo"""
        self.stdout.write('⚙️  Configurando parámetros del sistema...')
        
        if self.reset:
            ParametroSistema.objects.all().delete()
        
        parametros = self._obtener_parametros_sistema()
        
        creados = 0
        existentes = 0
        
        for param_data in parametros:
            param, created = ParametroSistema.objects.get_or_create(
                modulo=param_data['modulo'],
                clave=param_data['clave'],
                defaults=param_data
            )
            
            if created:
                creados += 1
            else:
                existentes += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✅ {creados} parámetros creados')
        )
        if existentes > 0:
            self.stdout.write(
                self.style.WARNING(f'  ℹ️  {existentes} parámetros ya existían')
            )
        
        self.parametros_creados = creados
        self.parametros_existentes = existentes

    def _obtener_parametros_sistema(self):
        """Retorna lista de parámetros del sistema"""
        return [
            # ==========================================
            # PARÁMETROS DE INVENTARIO
            # ==========================================
            {
                'modulo': 'inventory',
                'clave': 'peso_conversion_arroba',
                'nombre': 'Conversión de Arroba a Kilogramos',
                'descripcion': 'Factor de conversión de arroba a kg (1 arroba = X kg)',
                'tipo_dato': 'DECIMAL',
                'valor': '25.0',
                'valor_default': '25.0',
                'grupo': 'Conversiones',
                'orden': 1,
                'activo': True,
            },
            {
                'modulo': 'inventory',
                'clave': 'peso_conversion_libra',
                'nombre': 'Conversión de Libra a Kilogramos',
                'descripcion': 'Factor de conversión de libra a kg (1 libra = X kg)',
                'tipo_dato': 'DECIMAL',
                'valor': '0.453592',
                'valor_default': '0.453592',
                'grupo': 'Conversiones',
                'orden': 2,
                'activo': True,
            },
            {
                'modulo': 'inventory',
                'clave': 'alerta_stock_critico_quintales',
                'nombre': 'Alerta Stock Crítico Quintales',
                'descripcion': 'Porcentaje de peso restante para considerar quintal crítico',
                'tipo_dato': 'DECIMAL',
                'valor': '10.0',
                'valor_default': '10.0',
                'grupo': 'Alertas',
                'orden': 3,
                'activo': True,
            },
            {
                'modulo': 'inventory',
                'clave': 'alerta_stock_bajo_quintales',
                'nombre': 'Alerta Stock Bajo Quintales',
                'descripcion': 'Porcentaje de peso restante para considerar quintal bajo',
                'tipo_dato': 'DECIMAL',
                'valor': '25.0',
                'valor_default': '25.0',
                'grupo': 'Alertas',
                'orden': 4,
                'activo': True,
            },
            {
                'modulo': 'inventory',
                'clave': 'permitir_venta_stock_cero',
                'nombre': 'Permitir Venta con Stock Cero',
                'descripcion': 'Permite realizar ventas cuando el stock es cero',
                'tipo_dato': 'BOOLEAN',
                'valor': 'false',
                'valor_default': 'false',
                'grupo': 'Ventas',
                'orden': 5,
                'activo': True,
            },
            
            # ==========================================
            # PARÁMETROS DE VENTAS
            # ==========================================
            {
                'modulo': 'sales',
                'clave': 'descuento_maximo_categoria_alimentos',
                'nombre': 'Descuento Máximo - Alimentos',
                'descripcion': 'Descuento máximo permitido para categoría de alimentos (%)',
                'tipo_dato': 'DECIMAL',
                'valor': '10.0',
                'valor_default': '10.0',
                'grupo': 'Descuentos',
                'orden': 1,
                'activo': True,
            },
            {
                'modulo': 'sales',
                'clave': 'descuento_maximo_categoria_bebidas',
                'nombre': 'Descuento Máximo - Bebidas',
                'descripcion': 'Descuento máximo permitido para categoría de bebidas (%)',
                'tipo_dato': 'DECIMAL',
                'valor': '15.0',
                'valor_default': '15.0',
                'grupo': 'Descuentos',
                'orden': 2,
                'activo': True,
            },
            {
                'modulo': 'sales',
                'clave': 'precio_minimo_venta_quintal',
                'nombre': 'Precio Mínimo Venta Quintal',
                'descripcion': 'Precio mínimo por kg de quintal (evita ventas a pérdida)',
                'tipo_dato': 'DECIMAL',
                'valor': '0.50',
                'valor_default': '0.50',
                'grupo': 'Precios',
                'orden': 3,
                'activo': True,
            },
            {
                'modulo': 'sales',
                'clave': 'generar_factura_automatica',
                'nombre': 'Generar Factura Automática',
                'descripcion': 'Genera factura automáticamente después de cada venta',
                'tipo_dato': 'BOOLEAN',
                'valor': 'true',
                'valor_default': 'true',
                'grupo': 'Facturación',
                'orden': 4,
                'activo': True,
            },
            {
                'modulo': 'sales',
                'clave': 'imprimir_ticket_automatico',
                'nombre': 'Imprimir Ticket Automático',
                'descripcion': 'Imprime ticket automáticamente después de venta',
                'tipo_dato': 'BOOLEAN',
                'valor': 'true',
                'valor_default': 'true',
                'grupo': 'Impresión',
                'orden': 5,
                'activo': True,
            },
            
            # ==========================================
            # PARÁMETROS FINANCIEROS
            # ==========================================
            {
                'modulo': 'financial',
                'clave': 'permitir_cierre_caja_diferencia',
                'nombre': 'Permitir Cierre con Diferencia',
                'descripcion': 'Permite cerrar caja aunque haya diferencia',
                'tipo_dato': 'BOOLEAN',
                'valor': 'true',
                'valor_default': 'true',
                'grupo': 'Caja',
                'orden': 1,
                'activo': True,
            },
            {
                'modulo': 'financial',
                'clave': 'diferencia_maxima_cierre_caja',
                'nombre': 'Diferencia Máxima Cierre Caja',
                'descripcion': 'Diferencia máxima permitida al cerrar caja',
                'tipo_dato': 'DECIMAL',
                'valor': '5.00',
                'valor_default': '5.00',
                'grupo': 'Caja',
                'orden': 2,
                'activo': True,
            },
            {
                'modulo': 'financial',
                'clave': 'alerta_caja_chica_minima',
                'nombre': 'Alerta Caja Chica Mínima',
                'descripcion': 'Monto mínimo antes de alerta de caja chica',
                'tipo_dato': 'DECIMAL',
                'valor': '20.00',
                'valor_default': '20.00',
                'grupo': 'Caja Chica',
                'orden': 3,
                'activo': True,
            },
            
            # ==========================================
            # PARÁMETROS DE REPORTES
            # ==========================================
            {
                'modulo': 'reports',
                'clave': 'dias_retencion_reportes',
                'nombre': 'Días Retención de Reportes',
                'descripcion': 'Días para mantener reportes generados antes de eliminar',
                'tipo_dato': 'INTEGER',
                'valor': '90',
                'valor_default': '90',
                'grupo': 'Limpieza',
                'orden': 1,
                'activo': True,
            },
            {
                'modulo': 'reports',
                'clave': 'generar_reporte_diario_automatico',
                'nombre': 'Generar Reporte Diario Automático',
                'descripcion': 'Genera reporte diario automáticamente al cierre',
                'tipo_dato': 'BOOLEAN',
                'valor': 'true',
                'valor_default': 'true',
                'grupo': 'Automatización',
                'orden': 2,
                'activo': True,
            },
            
            # ==========================================
            # PARÁMETROS DE NOTIFICACIONES
            # ==========================================
            {
                'modulo': 'notifications',
                'clave': 'hora_envio_reporte_diario',
                'nombre': 'Hora Envío Reporte Diario',
                'descripcion': 'Hora para enviar reporte diario por email (formato HH:MM)',
                'tipo_dato': 'STRING',
                'valor': '18:00',
                'valor_default': '18:00',
                'grupo': 'Horarios',
                'orden': 1,
                'activo': True,
            },
            {
                'modulo': 'notifications',
                'clave': 'frecuencia_alertas_stock',
                'nombre': 'Frecuencia Alertas Stock',
                'descripcion': 'Frecuencia de envío de alertas de stock (DIARIO, SEMANAL)',
                'tipo_dato': 'STRING',
                'valor': 'DIARIO',
                'valor_default': 'DIARIO',
                'grupo': 'Frecuencias',
                'orden': 2,
                'activo': True,
            },
            
            # ==========================================
            # PARÁMETROS DE HARDWARE
            # ==========================================
            {
                'modulo': 'hardware',
                'clave': 'impresora_predeterminada',
                'nombre': 'Impresora Predeterminada',
                'descripcion': 'Nombre de la impresora predeterminada para tickets',
                'tipo_dato': 'STRING',
                'valor': 'EPSON TM-T20',
                'valor_default': 'EPSON TM-T20',
                'grupo': 'Impresoras',
                'orden': 1,
                'activo': True,
            },
            {
                'modulo': 'hardware',
                'clave': 'puerto_bascula',
                'nombre': 'Puerto Báscula',
                'descripcion': 'Puerto serial de la báscula (ej: COM3, /dev/ttyUSB0)',
                'tipo_dato': 'STRING',
                'valor': 'COM3',
                'valor_default': 'COM3',
                'grupo': 'Básculas',
                'orden': 2,
                'activo': True,
            },
            {
                'modulo': 'hardware',
                'clave': 'velocidad_bascula',
                'nombre': 'Velocidad Báscula (baud rate)',
                'descripcion': 'Velocidad de comunicación con báscula',
                'tipo_dato': 'INTEGER',
                'valor': '9600',
                'valor_default': '9600',
                'grupo': 'Básculas',
                'orden': 3,
                'activo': True,
            },
        ]

    # ========================================================================
    # PARTE 2: CONFIGURACIÓN OPERATIVA
    # ========================================================================

    def _crear_usuario_admin(self):
        """Crear usuario administrador si no existe"""
        self.stdout.write('👤 Configurando usuario administrador...')
        
        if self.reset:
            User.objects.filter(username='admin').delete()
        
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@commercebox.com',
                password=self.admin_password,
                first_name='Administrador',
                last_name='CommerceBox'
            )
            self.stdout.write(
                self.style.SUCCESS('  ✅ Usuario administrador creado')
            )
            self.stdout.write(
                self.style.WARNING(f'     Usuario: admin')
            )
            self.stdout.write(
                self.style.WARNING(f'     Password: {self.admin_password}')
            )
            self.admin_creado = True
            self.admin_user = admin_user
        else:
            self.stdout.write(
                self.style.WARNING('  ℹ️  Usuario administrador ya existe')
            )
            self.admin_creado = False
            self.admin_user = User.objects.get(username='admin')

    def _configurar_inventario(self):
        """Crear ConfiguracionInventario"""
        self.stdout.write('📦 Configurando inventario...')
        
        if self.reset:
            ConfiguracionInventario.objects.all().delete()
        
        config, created = ConfiguracionInventario.objects.get_or_create(
            defaults={
                'prefijo_codigo_quintal': 'CBX-QNT',
                'prefijo_codigo_producto': 'CBX-PRD',
                'dias_vencimiento_alerta': 30,
                'porcentaje_stock_bajo': 20,
                'porcentaje_stock_critico': 10,
                'unidades_peso_disponibles': ['kg', 'lb', 'arroba', 'quintal'],
                'creado_por': self.admin_user
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('  ✅ ConfiguracionInventario creada')
            )
            self.config_inventario_creada = True
        else:
            self.stdout.write(
                self.style.WARNING('  ℹ️  ConfiguracionInventario ya existe')
            )
            self.config_inventario_creada = False

    def _crear_categorias(self):
        """Crear categorías por defecto"""
        self.stdout.write('📁 Creando categorías de productos...')
        
        if self.reset:
            Categoria.objects.all().delete()
        
        categorias_default = [
            ('ALM', 'Alimentos', 'Productos alimenticios y comestibles', 25.0, 10.0),
            ('BEB', 'Bebidas', 'Bebidas, refrescos y jugos', 30.0, 15.0),
            ('LIM', 'Limpieza', 'Productos de limpieza y aseo', 35.0, 10.0),
            ('MED', 'Medicinas', 'Productos farmacéuticos y medicamentos', 40.0, 5.0),
            ('ACC', 'Accesorios', 'Accesorios y productos varios', 50.0, 10.0),
        ]
        
        creadas = 0
        existentes = 0
        
        for codigo, nombre, descripcion, margen, descuento in categorias_default:
            categoria, created = Categoria.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'margen_ganancia': margen,
                    'descuento_maximo': descuento,
                    'activo': True,
                    'creado_por': self.admin_user
                }
            )
            if created:
                creadas += 1
            else:
                existentes += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✅ {creadas} categorías creadas')
        )
        if existentes > 0:
            self.stdout.write(
                self.style.WARNING(f'  ℹ️  {existentes} categorías ya existían')
            )
        
        self.categorias_creadas = creadas
        self.categorias_existentes = existentes

    def _crear_marcas(self):
        """Crear marcas por defecto"""
        self.stdout.write('🏷️  Creando marcas de productos...')
        
        if self.reset:
            Marca.objects.all().delete()
        
        marcas_default = [
            ('GEN', 'Genérica', 'Sin marca específica', 'Genérico', 'Local'),
            ('NAC', 'Nacional', 'Marca Nacional S.A.', 'Nacional', 'Ecuador'),
            ('IMP', 'Importada', 'Marca Importada Inc.', 'Importada', 'Internacional'),
        ]
        
        creadas = 0
        existentes = 0
        
        for codigo, nombre, descripcion, fabricante, pais in marcas_default:
            marca, created = Marca.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fabricante': fabricante,
                    'pais_origen': pais,
                    'activo': True,
                    'creado_por': self.admin_user
                }
            )
            if created:
                creadas += 1
            else:
                existentes += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✅ {creadas} marcas creadas')
        )
        if existentes > 0:
            self.stdout.write(
                self.style.WARNING(f'  ℹ️  {existentes} marcas ya existían')
            )
        
        self.marcas_creadas = creadas
        self.marcas_existentes = existentes

    def _crear_proveedor(self):
        """Crear proveedor por defecto"""
        self.stdout.write('🏢 Creando proveedor general...')
        
        if self.reset:
            Proveedor.objects.filter(codigo='PROV001').delete()
        
        proveedor, created = Proveedor.objects.get_or_create(
            codigo='PROV001',
            defaults={
                'nombre': 'Proveedor General',
                'razon_social': 'Proveedor General S.A.',
                'ruc': '0000000000001',
                'telefono': '000-000-0000',
                'email': 'proveedor@ejemplo.com',
                'direccion': 'Dirección del proveedor',
                'ciudad': 'Ciudad',
                'pais': 'Ecuador',
                'limite_credito': Decimal('10000.00'),
                'dias_credito': 30,
                'activo': True,
                'creado_por': self.admin_user
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('  ✅ Proveedor general creado')
            )
            self.proveedor_creado = True
        else:
            self.stdout.write(
                self.style.WARNING('  ℹ️  Proveedor general ya existe')
            )
            self.proveedor_creado = False

    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================

    def _mostrar_resumen(self):
        """Mostrar resumen de configuración"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(
            self.style.SUCCESS('✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE')
        )
        self.stdout.write('=' * 70)
        
        # Resumen de creación
        self.stdout.write('\n📊 RESUMEN DE CONFIGURACIÓN:\n')
        
        # Sistema
        self.stdout.write('  🔧 SISTEMA:')
        if hasattr(self, 'config_sistema_creada') and self.config_sistema_creada:
            self.stdout.write('     ✅ ConfiguracionSistema creada')
        else:
            self.stdout.write('     ℹ️  ConfiguracionSistema ya existía')
        
        if hasattr(self, 'parametros_creados'):
            self.stdout.write(f'     ✅ {self.parametros_creados} parámetros del sistema')
            if self.parametros_existentes > 0:
                self.stdout.write(f'     ℹ️  {self.parametros_existentes} parámetros ya existían')
        
        # Usuario
        self.stdout.write('\n  👤 USUARIO:')
        if hasattr(self, 'admin_creado') and self.admin_creado:
            self.stdout.write('     ✅ Usuario administrador creado')
        elif not self.skip_admin:
            self.stdout.write('     ℹ️  Usuario administrador ya existía')
        else:
            self.stdout.write('     ⏭️  Creación de admin omitida')
        
        # Inventario
        self.stdout.write('\n  📦 INVENTARIO:')
        if hasattr(self, 'config_inventario_creada') and self.config_inventario_creada:
            self.stdout.write('     ✅ ConfiguracionInventario creada')
        else:
            self.stdout.write('     ℹ️  ConfiguracionInventario ya existía')
        
        if hasattr(self, 'categorias_creadas'):
            self.stdout.write(f'     ✅ {self.categorias_creadas} categorías de productos')
            if self.categorias_existentes > 0:
                self.stdout.write(f'     ℹ️  {self.categorias_existentes} categorías ya existían')
        
        if hasattr(self, 'marcas_creadas'):
            self.stdout.write(f'     ✅ {self.marcas_creadas} marcas de productos')
            if self.marcas_existentes > 0:
                self.stdout.write(f'     ℹ️  {self.marcas_existentes} marcas ya existían')
        
        if hasattr(self, 'proveedor_creado') and self.proveedor_creado:
            self.stdout.write('     ✅ Proveedor general creado')
        else:
            self.stdout.write('     ℹ️  Proveedor general ya existía')
        
        # Credenciales
        if hasattr(self, 'admin_creado') and self.admin_creado:
            self.stdout.write('\n🔑 CREDENCIALES DE ACCESO:')
            self.stdout.write('     Usuario: admin')
            self.stdout.write(f'     Password: {self.admin_password}')
            self.stdout.write('     ⚠️  IMPORTANTE: Cambiar password en producción')
        
        # URLs importantes
        self.stdout.write('\n🌐 ACCESOS PRINCIPALES:')
        self.stdout.write('     Admin Django: http://localhost:8000/admin/')
        self.stdout.write('     Configuración: http://localhost:8000/configuracion/')
        self.stdout.write('     Inventario: http://localhost:8000/inventario/')
        
        # Próximos pasos
        self.stdout.write('\n📋 PRÓXIMOS PASOS:')
        self.stdout.write('     1. Iniciar sesión en el admin')
        self.stdout.write('     2. Configurar datos de la empresa en Configuración del Sistema')
        self.stdout.write('     3. Ajustar parámetros según necesidades')
        self.stdout.write('     4. Comenzar a cargar productos')
        self.stdout.write('     5. ¡Empezar a vender!')
        
        # Comandos útiles
        self.stdout.write('\n🔧 COMANDOS ÚTILES:')
        self.stdout.write('     python manage.py backup_system --tipo MANUAL')
        self.stdout.write('     python manage.py system_health_check --verbose')
        self.stdout.write('     python manage.py runserver')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(
            self.style.SUCCESS('🎉 ¡COMMERCEBOX ESTÁ LISTO PARA USAR!')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')