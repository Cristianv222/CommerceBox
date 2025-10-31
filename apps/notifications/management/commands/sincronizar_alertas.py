# apps/notifications/management/commands/sincronizar_alertas.py

from django.core.management.base import BaseCommand
from apps.stock_alert_system.models import AlertaStock
from apps.notifications.models import Notificacion, TipoNotificacion
from apps.authentication.models import Usuario


class Command(BaseCommand):
    help = 'Convierte alertas activas en notificaciones'

    def handle(self, *args, **kwargs):
        self.stdout.write('🔄 Sincronizando alertas con notificaciones...\n')
        
        # Verificar que existan tipos de notificación
        if TipoNotificacion.objects.count() == 0:
            self.stdout.write(self.style.ERROR('❌ No hay tipos de notificación. Ejecuta primero: crear_tipos_notificaciones'))
            return
        
        # Obtener alertas activas
        alertas = AlertaStock.objects.filter(resuelta=False).select_related('producto')
        
        if alertas.count() == 0:
            self.stdout.write(self.style.WARNING('⚠️  No hay alertas activas'))
            return
        
        self.stdout.write(f'📊 Encontradas {alertas.count()} alertas activas\n')
        
        # Obtener usuarios administradores y supervisores
        usuarios = Usuario.objects.filter(
            rol__codigo__in=['ADMIN', 'SUPERVISOR'],
            estado='ACTIVO'
        )
        
        if usuarios.count() == 0:
            self.stdout.write(self.style.ERROR('❌ No hay usuarios ADMIN o SUPERVISOR activos'))
            return
        
        self.stdout.write(f'👥 Notificando a {usuarios.count()} usuarios\n')
        
        # Mapeo de tipos de alerta a tipos de notificación
        tipo_map = {
            'STOCK_BAJO': 'STOCK_BAJO',
            'STOCK_CRITICO': 'STOCK_CRITICO',
            'STOCK_AGOTADO': 'STOCK_AGOTADO',
            'QUINTAL_CRITICO': 'STOCK_CRITICO_QUINTAL',
            'QUINTAL_AGOTADO': 'QUINTAL_AGOTADO',
            'VENCIMIENTO_PROXIMO': 'VENCIMIENTO_PROXIMO',
        }
        
        creadas = 0
        errores = 0
        
        for alerta in alertas:
            # Determinar código del tipo de notificación
            tipo_codigo = tipo_map.get(alerta.tipo_alerta, 'ALERTA_SISTEMA')
            
            try:
                # Obtener tipo de notificación
                tipo_notif = TipoNotificacion.objects.get(codigo=tipo_codigo, activo=True)
                
                # Crear notificación para cada usuario
                for usuario in usuarios:
                    # Verificar si ya existe notificación para esta alerta y usuario
                    existe = Notificacion.objects.filter(
                        usuario=usuario,
                        titulo=alerta.titulo,
                        estado__in=['PENDIENTE', 'ENVIADA']
                    ).exists()
                    
                    if not existe:
                        Notificacion.objects.create(
                            tipo_notificacion=tipo_notif,
                            usuario=usuario,
                            titulo=alerta.titulo,
                            mensaje=alerta.mensaje,
                            prioridad=alerta.prioridad,
                            requiere_accion=True,
                            datos_adicionales=alerta.datos_adicionales,
                            estado='ENVIADA',
                            enviada_web=True
                        )
                        creadas += 1
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ {alerta.titulo}'))
                
            except TipoNotificacion.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  ❌ Tipo {tipo_codigo} no existe: {alerta.titulo}'))
                errores += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error: {str(e)}'))
                errores += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Sincronización completada: {creadas} notificaciones creadas, {errores} errores'))