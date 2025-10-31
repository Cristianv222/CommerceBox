# apps/notifications/management/commands/crear_tipos_notificaciones.py

from django.core.management.base import BaseCommand
from apps.notifications.models import TipoNotificacion, ConfiguracionNotificacion


class Command(BaseCommand):
    help = 'Crea los tipos de notificaciones iniciales del sistema'

    def handle(self, *args, **kwargs):
        self.stdout.write('🚀 Creando tipos de notificaciones...\n')
        
        tipos_notificaciones = [
            # STOCK
            {
                'codigo': 'STOCK_CRITICO',
                'nombre': 'Stock Crítico',
                'descripcion': 'Producto en nivel crítico',
                'categoria': 'STOCK',
                'prioridad_default': 'CRITICA',
                'plantilla_titulo': '🔴 Stock Crítico: {producto}',
                'plantilla_mensaje': 'Stock crítico detectado',
                'requiere_accion': True,
                'enviar_email': True,
                'enviar_push': True,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN', 'SUPERVISOR']
            },
            {
                'codigo': 'STOCK_BAJO',
                'nombre': 'Stock Bajo',
                'descripcion': 'Stock por debajo del ideal',
                'categoria': 'STOCK',
                'prioridad_default': 'ALTA',
                'plantilla_titulo': '🟡 Stock Bajo: {producto}',
                'plantilla_mensaje': 'Stock bajo detectado',
                'requiere_accion': True,
                'enviar_email': True,
                'enviar_push': False,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN', 'SUPERVISOR']
            },
            {
                'codigo': 'STOCK_AGOTADO',
                'nombre': 'Stock Agotado',
                'descripcion': 'Producto sin stock',
                'categoria': 'STOCK',
                'prioridad_default': 'CRITICA',
                'plantilla_titulo': '⚫ Stock Agotado: {producto}',
                'plantilla_mensaje': 'Stock agotado',
                'requiere_accion': True,
                'enviar_email': True,
                'enviar_push': True,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN', 'SUPERVISOR']
            },
            {
                'codigo': 'STOCK_CRITICO_QUINTAL',
                'nombre': 'Quintal Crítico',
                'descripcion': 'Quintal en estado crítico',
                'categoria': 'STOCK',
                'prioridad_default': 'CRITICA',
                'plantilla_titulo': '🚨 Quintal Crítico: {producto}',
                'plantilla_mensaje': 'Quintal en estado crítico',
                'requiere_accion': True,
                'enviar_email': True,
                'enviar_push': True,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN', 'SUPERVISOR']
            },
            {
                'codigo': 'QUINTAL_AGOTADO',
                'nombre': 'Quintal Agotado',
                'descripcion': 'Quintal completamente vendido',
                'categoria': 'STOCK',
                'prioridad_default': 'MEDIA',
                'plantilla_titulo': '⚫ Quintal Agotado: {producto}',
                'plantilla_mensaje': 'Quintal agotado',
                'requiere_accion': False,
                'enviar_email': False,
                'enviar_push': False,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN', 'SUPERVISOR']
            },
            {
                'codigo': 'VENCIMIENTO_PROXIMO',
                'nombre': 'Vencimiento Próximo',
                'descripcion': 'Producto próximo a vencer',
                'categoria': 'STOCK',
                'prioridad_default': 'ALTA',
                'plantilla_titulo': '⏰ Vencimiento Próximo: {producto}',
                'plantilla_mensaje': 'Producto próximo a vencer',
                'requiere_accion': True,
                'enviar_email': True,
                'enviar_push': False,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN', 'SUPERVISOR']
            },
            {
                'codigo': 'ALERTA_SISTEMA',
                'nombre': 'Alerta del Sistema',
                'descripcion': 'Alerta genérica',
                'categoria': 'SISTEMA',
                'prioridad_default': 'MEDIA',
                'plantilla_titulo': '⚠️ Alerta',
                'plantilla_mensaje': 'Alerta del sistema',
                'requiere_accion': False,
                'enviar_email': False,
                'enviar_push': False,
                'enviar_sms': False,
                'roles_destinatarios': ['ADMIN']
            },
        ]
        
        creados = 0
        actualizados = 0
        
        for tipo_data in tipos_notificaciones:
            tipo, created = TipoNotificacion.objects.update_or_create(
                codigo=tipo_data['codigo'],
                defaults=tipo_data
            )
            
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ Creado: {tipo.nombre}'))
            else:
                actualizados += 1
                self.stdout.write(self.style.WARNING(f'  ♻️  Actualizado: {tipo.nombre}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Proceso completado: {creados} creados, {actualizados} actualizados'))
        
        # Crear configuración si no existe
        config = ConfiguracionNotificacion.get_config()
        self.stdout.write(self.style.SUCCESS('✅ Configuración inicializada'))