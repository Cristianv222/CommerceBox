# apps/financial_management/cash_management/cash_service.py

"""
Servicio principal para gestión de operaciones de caja
Maneja la lógica de negocio compleja de apertura, cierre y movimientos
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ..models import Caja, MovimientoCaja, ArqueoCaja


class CashService:
    """Servicio centralizado para operaciones de caja"""
    
    @staticmethod
    @transaction.atomic
    def abrir_caja(
        caja: Caja,
        usuario,
        monto_inicial: Decimal,
        observaciones: str = ""
    ) -> MovimientoCaja:
        """
        Abre una caja con validaciones completas
        
        Args:
            caja: Instancia de Caja a abrir
            usuario: Usuario que abre la caja
            monto_inicial: Monto con el que se abre
            observaciones: Observaciones opcionales
            
        Returns:
            MovimientoCaja: Movimiento de apertura creado
            
        Raises:
            ValueError: Si la caja ya está abierta o validaciones fallan
        """
        # Validaciones
        if caja.estado == 'ABIERTA':
            raise ValueError(f"La caja {caja.nombre} ya está abierta")
        
        if monto_inicial < 0:
            raise ValueError("El monto de apertura no puede ser negativo")
        
        # Verificar si el usuario tiene otra caja abierta
        caja_activa_usuario = Caja.objects.filter(
            usuario_apertura=usuario,
            estado='ABIERTA'
        ).exclude(pk=caja.pk).first()
        
        if caja_activa_usuario:
            raise ValueError(
                f"El usuario ya tiene la caja '{caja_activa_usuario.nombre}' abierta. "
                "Debe cerrarla primero."
            )
        
        # Abrir caja
        caja.estado = 'ABIERTA'
        caja.monto_apertura = monto_inicial
        caja.monto_actual = monto_inicial
        caja.fecha_apertura = timezone.now()
        caja.usuario_apertura = usuario
        caja.fecha_cierre = None
        caja.usuario_cierre = None
        caja.save()
        
        # Registrar movimiento de apertura
        movimiento = MovimientoCaja.objects.create(
            caja=caja,
            tipo_movimiento='APERTURA',
            monto=monto_inicial,
            saldo_anterior=Decimal('0.00'),
            saldo_nuevo=monto_inicial,
            usuario=usuario,
            observaciones=observaciones or f"Apertura de caja con ${monto_inicial}"
        )
        
        return movimiento
    
    @staticmethod
    @transaction.atomic
    def cerrar_caja(
        caja: Caja,
        usuario,
        monto_contado: Decimal,
        desglose_efectivo: Dict[str, int],
        observaciones: str = "",
        observaciones_diferencia: str = ""
    ) -> Tuple[ArqueoCaja, Decimal]:
        """
        Cierra una caja y genera arqueo automático
        
        Args:
            caja: Instancia de Caja a cerrar
            usuario: Usuario que cierra
            monto_contado: Total contado físicamente
            desglose_efectivo: Dict con billetes y monedas
            observaciones: Observaciones generales
            observaciones_diferencia: Explicación de diferencia si existe
            
        Returns:
            Tuple[ArqueoCaja, Decimal]: Arqueo generado y diferencia
            
        Raises:
            ValueError: Si validaciones fallan
        """
        # Validaciones
        if caja.estado == 'CERRADA':
            raise ValueError(f"La caja {caja.nombre} ya está cerrada")
        
        if caja.requiere_autorizacion_cierre:
            if usuario.rol not in ['SUPERVISOR', 'ADMIN']:
                raise ValueError(
                    "Esta caja requiere autorización de supervisor para cerrar"
                )
        
        # Calcular diferencia
        monto_esperado = caja.monto_actual
        diferencia = monto_contado - monto_esperado
        
        # Si hay diferencia significativa, requerir explicación
        if abs(diferencia) > Decimal('1.00') and not observaciones_diferencia:
            raise ValueError(
                f"Diferencia de ${abs(diferencia):.2f}. "
                "Debe proporcionar una explicación."
            )
        
        # Obtener estadísticas de la sesión
        movimientos_sesion = MovimientoCaja.objects.filter(
            caja=caja,
            fecha_movimiento__gte=caja.fecha_apertura
        )
        
        total_ventas = movimientos_sesion.filter(
            tipo_movimiento='VENTA'
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')
        
        total_ingresos = movimientos_sesion.filter(
            tipo_movimiento__in=['INGRESO', 'AJUSTE_POSITIVO']
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')
        
        total_retiros = movimientos_sesion.filter(
            tipo_movimiento__in=['RETIRO', 'AJUSTE_NEGATIVO']
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')
        
        # Generar número de arqueo
        numero_arqueo = CashService._generar_numero_arqueo()
        
        # Crear arqueo
        arqueo = ArqueoCaja.objects.create(
            numero_arqueo=numero_arqueo,
            caja=caja,
            fecha_apertura=caja.fecha_apertura,
            fecha_cierre=timezone.now(),
            monto_apertura=caja.monto_apertura,
            total_ventas=total_ventas,
            total_ingresos=total_ingresos,
            total_retiros=total_retiros,
            monto_esperado=monto_esperado,
            monto_contado=monto_contado,
            billetes_100=desglose_efectivo.get('billetes_100', 0),
            billetes_50=desglose_efectivo.get('billetes_50', 0),
            billetes_20=desglose_efectivo.get('billetes_20', 0),
            billetes_10=desglose_efectivo.get('billetes_10', 0),
            billetes_5=desglose_efectivo.get('billetes_5', 0),
            billetes_1=desglose_efectivo.get('billetes_1', 0),
            monedas=desglose_efectivo.get('monedas', Decimal('0.00')),
            diferencia=diferencia,
            observaciones=observaciones,
            observaciones_diferencia=observaciones_diferencia,
            usuario_apertura=caja.usuario_apertura,
            usuario_cierre=usuario
        )
        
        # Registrar movimiento de cierre
        MovimientoCaja.objects.create(
            caja=caja,
            tipo_movimiento='CIERRE',
            monto=monto_contado,
            saldo_anterior=monto_esperado,
            saldo_nuevo=Decimal('0.00'),
            usuario=usuario,
            observaciones=f"Cierre de caja - Arqueo: {numero_arqueo}"
        )
        
        # Cerrar caja
        caja.estado = 'CERRADA'
        caja.fecha_cierre = timezone.now()
        caja.usuario_cierre = usuario
        caja.monto_actual = Decimal('0.00')
        caja.save()
        
        return arqueo, diferencia
    
    @staticmethod
    @transaction.atomic
    def registrar_movimiento(
        caja: Caja,
        tipo_movimiento: str,
        monto: Decimal,
        usuario,
        observaciones: str = "",
        venta=None
    ) -> MovimientoCaja:
        """
        Registra un movimiento de caja
        
        Args:
            caja: Caja donde se registra
            tipo_movimiento: Tipo del movimiento
            monto: Monto del movimiento
            usuario: Usuario que registra
            observaciones: Observaciones
            venta: Venta asociada (opcional)
            
        Returns:
            MovimientoCaja: Movimiento creado
            
        Raises:
            ValueError: Si validaciones fallan
        """
        # Validaciones
        if caja.estado != 'ABIERTA':
            raise ValueError("No se pueden registrar movimientos en una caja cerrada")
        
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        
        # Validar fondos suficientes para retiros
        if tipo_movimiento in ['RETIRO', 'AJUSTE_NEGATIVO']:
            if monto > caja.monto_actual:
                raise ValueError(
                    f"Fondos insuficientes. Disponible: ${caja.monto_actual:.2f}"
                )
        
        # Calcular nuevo saldo
        saldo_anterior = caja.monto_actual
        
        if tipo_movimiento in ['INGRESO', 'AJUSTE_POSITIVO', 'VENTA']:
            caja.monto_actual += monto
        else:  # RETIRO, AJUSTE_NEGATIVO
            caja.monto_actual -= monto
        
        caja.save()
        
        # Crear movimiento
        movimiento = MovimientoCaja.objects.create(
            caja=caja,
            tipo_movimiento=tipo_movimiento,
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=caja.monto_actual,
            usuario=usuario,
            observaciones=observaciones,
            venta=venta
        )
        
        return movimiento
    
    @staticmethod
    def obtener_resumen_caja(caja: Caja) -> Dict:
        """
        Obtiene un resumen completo del estado de la caja
        
        Args:
            caja: Caja a consultar
            
        Returns:
            Dict con toda la información relevante
        """
        from django.db.models import Sum, Count
        
        resumen = {
            'caja': caja,
            'estado': caja.estado,
            'monto_actual': caja.monto_actual,
            'fecha_apertura': caja.fecha_apertura,
        }
        
        if caja.estado == 'ABIERTA':
            # Movimientos desde apertura
            movimientos = MovimientoCaja.objects.filter(
                caja=caja,
                fecha_movimiento__gte=caja.fecha_apertura
            )
            
            # Ventas
            ventas = movimientos.filter(tipo_movimiento='VENTA').aggregate(
                total=Sum('monto'),
                cantidad=Count('id')
            )
            resumen['ventas'] = {
                'total': ventas['total'] or Decimal('0.00'),
                'cantidad': ventas['cantidad'] or 0
            }
            
            # Ingresos
            resumen['ingresos'] = movimientos.filter(
                tipo_movimiento='INGRESO'
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            
            # Retiros
            resumen['retiros'] = movimientos.filter(
                tipo_movimiento='RETIRO'
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            
            # Monto esperado
            resumen['monto_esperado'] = (
                caja.monto_apertura +
                resumen['ventas']['total'] +
                resumen['ingresos'] -
                resumen['retiros']
            )
            
            # Tiempo abierta
            resumen['tiempo_abierta'] = timezone.now() - caja.fecha_apertura
        
        return resumen
    
    @staticmethod
    def _generar_numero_arqueo() -> str:
        """Genera número único de arqueo"""
        from django.db.models import Max
        
        ultimo = ArqueoCaja.objects.aggregate(
            max_num=Max('numero_arqueo')
        )['max_num']
        
        if ultimo:
            try:
                numero = int(ultimo.split('-')[-1]) + 1
            except:
                numero = 1
        else:
            numero = 1
        
        return f"ARQ-{timezone.now().year}-{numero:05d}"
    
    @staticmethod
    def validar_desglose_efectivo(
        billetes: Dict[str, int],
        monto_esperado: Decimal
    ) -> Tuple[bool, Decimal, str]:
        """
        Valida que el desglose de efectivo cuadre con el monto
        
        Args:
            billetes: Dict con cantidad de cada denominación
            monto_esperado: Monto que debería dar
            
        Returns:
            Tuple[bool, Decimal, str]: (válido, total_calculado, mensaje)
        """
        total = Decimal('0.00')
        
        denominaciones = {
            'billetes_100': 100,
            'billetes_50': 50,
            'billetes_20': 20,
            'billetes_10': 10,
            'billetes_5': 5,
            'billetes_1': 1,
        }
        
        for nombre, valor in denominaciones.items():
            cantidad = billetes.get(nombre, 0)
            total += Decimal(str(cantidad * valor))
        
        # Agregar monedas
        total += billetes.get('monedas', Decimal('0.00'))
        
        diferencia = abs(total - monto_esperado)
        
        if diferencia < Decimal('0.01'):
            return True, total, "El desglose cuadra correctamente"
        else:
            return False, total, f"Diferencia de ${diferencia:.2f}"