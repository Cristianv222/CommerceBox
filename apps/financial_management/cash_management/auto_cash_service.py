# apps/financial_management/cash_management/auto_cash_service.py

"""
Servicio de Auto-Gestión de Cajas
Gestiona la apertura automática de cajas con la primera venta del día
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, time
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AutoCashService:
    """Servicio para gestionar la apertura automática de cajas"""
    
    @staticmethod
    @transaction.atomic
    def obtener_o_crear_caja_activa(usuario, sucursal=None):
        """
        Obtiene la caja activa del usuario o crea una nueva automáticamente
        
        Lógica:
        1. Busca si el usuario tiene una caja ABIERTA hoy
        2. Si no existe, crea una nueva caja automáticamente
        3. Si existe una caja abierta de días anteriores, la mantiene (no la cierra)
        
        Args:
            usuario: Usuario que realiza la venta
            sucursal: Sucursal donde se realiza (opcional)
            
        Returns:
            tuple: (caja, fue_creada)
        """
        from ..models import Caja, MovimientoCaja
        
        # Buscar caja ABIERTA del usuario (sin importar la fecha)
        caja_abierta = Caja.objects.filter(
            usuario_apertura=usuario,
            estado='ABIERTA'
        ).first()
        
        if caja_abierta:
            logger.info(
                f"📦 Caja existente encontrada: {caja_abierta.nombre} - "
                f"Abierta desde {caja_abierta.fecha_apertura}"
            )
            return caja_abierta, False
        
        # No hay caja abierta - crear nueva
        logger.info(f"🆕 No hay caja abierta para {usuario.username} - Creando nueva...")
        
        # Obtener o crear la caja principal del usuario
        caja, caja_nueva = Caja.objects.get_or_create(
            codigo=f'CJA-{usuario.username.upper()[:10]}',
            defaults={
                'nombre': f'Caja {usuario.get_full_name() or usuario.username}',
                'tipo': 'PRINCIPAL',
                'requiere_autorizacion_cierre': False,
                'activa': True
            }
        )
        
        if caja_nueva:
            logger.info(f"✨ Caja creada: {caja.nombre} ({caja.codigo})")
        
        # Abrir la caja con monto inicial $0 (apertura automática)
        caja.estado = 'ABIERTA'
        caja.monto_apertura = Decimal('0.00')
        caja.monto_actual = Decimal('0.00')
        caja.fecha_apertura = timezone.now()
        caja.usuario_apertura = usuario
        caja.fecha_cierre = None
        caja.usuario_cierre = None
        caja.save()
        
        # Crear movimiento de apertura
        MovimientoCaja.objects.create(
            caja=caja,
            tipo_movimiento='APERTURA',
            monto=Decimal('0.00'),
            saldo_anterior=Decimal('0.00'),
            saldo_nuevo=Decimal('0.00'),
            usuario=usuario,
            observaciones='Apertura automática - Primera venta del usuario'
        )
        
        logger.info(
            f"✅ Caja {caja.nombre} abierta automáticamente para {usuario.username}"
        )
        
        return caja, True
    
    @staticmethod
    @transaction.atomic
    def registrar_venta_en_caja(venta, usuario):
        """
        Registra una venta en la caja activa (creándola si es necesario)
        
        Args:
            venta: Instancia del modelo Venta
            usuario: Usuario que realizó la venta
            
        Returns:
            MovimientoCaja: El movimiento creado
        """
        from ..models import MovimientoCaja
        
        # Obtener o crear caja activa
        caja, fue_creada = AutoCashService.obtener_o_crear_caja_activa(
            usuario=usuario,
            sucursal=getattr(venta, 'sucursal', None)
        )
        
        # Asignar caja a la venta si no tiene
        if not venta.caja:
            venta.caja = caja
            venta.save(update_fields=['caja'])
        
        # Calcular saldo anterior
        saldo_anterior = caja.monto_actual
        
        # Actualizar monto de la caja
        caja.monto_actual += venta.total
        caja.save(update_fields=['monto_actual'])
        
        # Registrar movimiento
        movimiento = MovimientoCaja.objects.create(
            caja=caja,
            tipo_movimiento='VENTA',
            monto=venta.total,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=caja.monto_actual,
            venta=venta,
            usuario=usuario,
            observaciones=f'Venta {venta.numero_venta}'
        )
        
        logger.info(
            f"💰 Venta registrada en caja: {venta.numero_venta} - "
            f"${venta.total} en {caja.nombre}"
        )
        
        return movimiento
    
    @staticmethod
    def obtener_caja_activa_usuario(usuario):
        """
        Obtiene la caja activa actual del usuario (sin crearla)
        
        Args:
            usuario: Usuario a consultar
            
        Returns:
            Caja o None
        """
        from ..models import Caja
        
        return Caja.objects.filter(
            usuario_apertura=usuario,
            estado='ABIERTA'
        ).first()
