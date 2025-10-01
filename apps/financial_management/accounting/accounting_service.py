# apps/financial_management/accounting/accounting_service.py

"""
Servicio de contabilidad automática
Genera asientos contables por cada operación financiera
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Optional
from datetime import datetime


class AccountingService:
    """Servicio para generar contabilidad automática"""
    
    # Catálogo de cuentas simplificado
    CUENTAS = {
        # ACTIVOS
        'CAJA_EFECTIVO': {'codigo': '1101', 'nombre': 'Caja y Efectivo', 'tipo': 'ACTIVO'},
        'BANCOS': {'codigo': '1102', 'nombre': 'Bancos', 'tipo': 'ACTIVO'},
        'CAJA_CHICA': {'codigo': '1103', 'nombre': 'Caja Chica', 'tipo': 'ACTIVO'},
        'INVENTARIO': {'codigo': '1201', 'nombre': 'Inventario de Mercaderías', 'tipo': 'ACTIVO'},
        'CUENTAS_POR_COBRAR': {'codigo': '1301', 'nombre': 'Cuentas por Cobrar Clientes', 'tipo': 'ACTIVO'},
        
        # PASIVOS
        'CUENTAS_POR_PAGAR': {'codigo': '2101', 'nombre': 'Cuentas por Pagar Proveedores', 'tipo': 'PASIVO'},
        
        # PATRIMONIO
        'CAPITAL': {'codigo': '3101', 'nombre': 'Capital', 'tipo': 'PATRIMONIO'},
        'UTILIDAD_EJERCICIO': {'codigo': '3301', 'nombre': 'Utilidad del Ejercicio', 'tipo': 'PATRIMONIO'},
        
        # INGRESOS
        'VENTAS': {'codigo': '4101', 'nombre': 'Ventas', 'tipo': 'INGRESO'},
        'OTROS_INGRESOS': {'codigo': '4201', 'nombre': 'Otros Ingresos', 'tipo': 'INGRESO'},
        
        # COSTOS
        'COSTO_VENTAS': {'codigo': '5101', 'nombre': 'Costo de Ventas', 'tipo': 'COSTO'},
        
        # GASTOS
        'GASTOS_ADMINISTRATIVOS': {'codigo': '6101', 'nombre': 'Gastos Administrativos', 'tipo': 'GASTO'},
        'GASTOS_OPERATIVOS': {'codigo': '6201', 'nombre': 'Gastos Operativos', 'tipo': 'GASTO'},
        'GASTOS_VARIOS': {'codigo': '6301', 'nombre': 'Gastos Varios', 'tipo': 'GASTO'},
    }
    
    @staticmethod
    @transaction.atomic
    def generar_asiento_venta(venta, metodo_pago: str = 'EFECTIVO') -> Dict:
        """
        Genera asiento contable por una venta
        
        Args:
            venta: Instancia de Venta
            metodo_pago: Método de pago (EFECTIVO, TARJETA, CREDITO)
            
        Returns:
            Dict con el asiento generado
        """
        asiento = {
            'fecha': timezone.now(),
            'concepto': f'Venta {venta.numero_venta}',
            'referencia': venta.numero_venta,
            'tipo': 'VENTA',
            'movimientos': []
        }
        
        # Calcular costo de venta
        costo_total = sum(
            detalle.costo_total for detalle in venta.detalles.all()
        )
        
        # === REGISTRO DE LA VENTA ===
        
        # 1. DEBE: Caja/Bancos/Cuentas por Cobrar (según forma de pago)
        if metodo_pago == 'EFECTIVO':
            cuenta_debe = 'CAJA_EFECTIVO'
        elif metodo_pago in ['TARJETA_DEBITO', 'TARJETA_CREDITO']:
            cuenta_debe = 'BANCOS'
        else:  # CREDITO
            cuenta_debe = 'CUENTAS_POR_COBRAR'
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS[cuenta_debe],
            'tipo_movimiento': 'DEBE',
            'monto': venta.total,
            'descripcion': f'Venta a {venta.cliente.nombre_completo() if venta.cliente else "Público General"}'
        })
        
        # 2. HABER: Ventas
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['VENTAS'],
            'tipo_movimiento': 'HABER',
            'monto': venta.subtotal,
            'descripcion': 'Ingreso por venta de mercaderías'
        })
        
        # 3. HABER: IVA (si aplica impuestos)
        if venta.impuestos > 0:
            asiento['movimientos'].append({
                'cuenta': {'codigo': '2201', 'nombre': 'IVA por Pagar', 'tipo': 'PASIVO'},
                'tipo_movimiento': 'HABER',
                'monto': venta.impuestos,
                'descripcion': 'IVA generado en venta'
            })
        
        # === REGISTRO DEL COSTO ===
        
        # 4. DEBE: Costo de Ventas
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['COSTO_VENTAS'],
            'tipo_movimiento': 'DEBE',
            'monto': costo_total,
            'descripcion': 'Costo de mercaderías vendidas'
        })
        
        # 5. HABER: Inventario
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['INVENTARIO'],
            'tipo_movimiento': 'HABER',
            'monto': costo_total,
            'descripcion': 'Salida de inventario por venta'
        })
        
        # Validar balance del asiento
        AccountingService._validar_balance(asiento)
        
        return asiento
    
    @staticmethod
    @transaction.atomic
    def generar_asiento_compra(compra) -> Dict:
        """
        Genera asiento contable por una compra a proveedor
        
        Args:
            compra: Instancia de Compra
            
        Returns:
            Dict con el asiento generado
        """
        asiento = {
            'fecha': timezone.now(),
            'concepto': f'Compra {compra.numero_compra}',
            'referencia': compra.numero_compra,
            'tipo': 'COMPRA',
            'movimientos': []
        }
        
        # 1. DEBE: Inventario
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['INVENTARIO'],
            'tipo_movimiento': 'DEBE',
            'monto': compra.subtotal,
            'descripcion': f'Compra a {compra.proveedor.nombre_comercial}'
        })
        
        # 2. DEBE: IVA (si aplica)
        if compra.impuestos > 0:
            asiento['movimientos'].append({
                'cuenta': {'codigo': '1401', 'nombre': 'IVA por Cobrar', 'tipo': 'ACTIVO'},
                'tipo_movimiento': 'DEBE',
                'monto': compra.impuestos,
                'descripcion': 'IVA pagado en compra'
            })
        
        # 3. HABER: Cuentas por Pagar o Caja
        cuenta_haber = 'CUENTAS_POR_PAGAR'  # Por defecto a crédito
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS[cuenta_haber],
            'tipo_movimiento': 'HABER',
            'monto': compra.total,
            'descripcion': f'Compra a crédito - {compra.proveedor.nombre_comercial}'
        })
        
        AccountingService._validar_balance(asiento)
        
        return asiento
    
    @staticmethod
    def generar_asiento_apertura_caja(caja, monto_apertura: Decimal) -> Dict:
        """
        Genera asiento por apertura de caja
        
        Args:
            caja: Instancia de Caja
            monto_apertura: Monto de apertura
            
        Returns:
            Dict con el asiento
        """
        asiento = {
            'fecha': timezone.now(),
            'concepto': f'Apertura de caja {caja.nombre}',
            'referencia': f'AP-{caja.codigo}',
            'tipo': 'APERTURA_CAJA',
            'movimientos': []
        }
        
        # Si el monto viene de banco
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['CAJA_EFECTIVO'],
            'tipo_movimiento': 'DEBE',
            'monto': monto_apertura,
            'descripcion': f'Apertura de {caja.nombre}'
        })
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['BANCOS'],
            'tipo_movimiento': 'HABER',
            'monto': monto_apertura,
            'descripcion': 'Retiro para apertura de caja'
        })
        
        return asiento
    
    @staticmethod
    def generar_asiento_cierre_caja(arqueo) -> Dict:
        """
        Genera asiento por cierre de caja
        
        Args:
            arqueo: Instancia de ArqueoCaja
            
        Returns:
            Dict con el asiento
        """
        asiento = {
            'fecha': timezone.now(),
            'concepto': f'Cierre de caja {arqueo.caja.nombre} - {arqueo.numero_arqueo}',
            'referencia': arqueo.numero_arqueo,
            'tipo': 'CIERRE_CAJA',
            'movimientos': []
        }
        
        # Depósito del efectivo al banco
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['BANCOS'],
            'tipo_movimiento': 'DEBE',
            'monto': arqueo.monto_contado,
            'descripcion': f'Depósito de cierre {arqueo.caja.nombre}'
        })
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['CAJA_EFECTIVO'],
            'tipo_movimiento': 'HABER',
            'monto': arqueo.monto_contado,
            'descripcion': f'Efectivo depositado al banco'
        })
        
        # Registrar diferencia si existe
        if arqueo.diferencia != 0:
            if arqueo.diferencia > 0:  # Sobrante
                asiento['movimientos'].append({
                    'cuenta': AccountingService.CUENTAS['CAJA_EFECTIVO'],
                    'tipo_movimiento': 'DEBE',
                    'monto': abs(arqueo.diferencia),
                    'descripcion': 'Sobrante de caja'
                })
                asiento['movimientos'].append({
                    'cuenta': AccountingService.CUENTAS['OTROS_INGRESOS'],
                    'tipo_movimiento': 'HABER',
                    'monto': abs(arqueo.diferencia),
                    'descripcion': 'Sobrante de caja'
                })
            else:  # Faltante
                asiento['movimientos'].append({
                    'cuenta': AccountingService.CUENTAS['GASTOS_VARIOS'],
                    'tipo_movimiento': 'DEBE',
                    'monto': abs(arqueo.diferencia),
                    'descripcion': 'Faltante de caja'
                })
                asiento['movimientos'].append({
                    'cuenta': AccountingService.CUENTAS['CAJA_EFECTIVO'],
                    'tipo_movimiento': 'HABER',
                    'monto': abs(arqueo.diferencia),
                    'descripcion': 'Faltante de caja'
                })
        
        return asiento
    
    @staticmethod
    def generar_asiento_gasto_caja_chica(movimiento_caja_chica) -> Dict:
        """
        Genera asiento por gasto de caja chica
        
        Args:
            movimiento_caja_chica: Instancia de MovimientoCajaChica
            
        Returns:
            Dict con el asiento
        """
        asiento = {
            'fecha': timezone.now(),
            'concepto': f'Gasto caja chica - {movimiento_caja_chica.get_categoria_gasto_display()}',
            'referencia': f'CCH-{movimiento_caja_chica.id}',
            'tipo': 'GASTO_CAJA_CHICA',
            'movimientos': []
        }
        
        # Determinar cuenta de gasto según categoría
        categoria = movimiento_caja_chica.categoria_gasto
        if categoria in ['LIMPIEZA', 'OFICINA', 'MANTENIMIENTO']:
            cuenta_gasto = 'GASTOS_OPERATIVOS'
        else:
            cuenta_gasto = 'GASTOS_VARIOS'
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS[cuenta_gasto],
            'tipo_movimiento': 'DEBE',
            'monto': movimiento_caja_chica.monto,
            'descripcion': movimiento_caja_chica.descripcion[:100]
        })
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['CAJA_CHICA'],
            'tipo_movimiento': 'HABER',
            'monto': movimiento_caja_chica.monto,
            'descripcion': f'Gasto {categoria}'
        })
        
        return asiento
    
    @staticmethod
    def generar_asiento_reposicion_caja_chica(movimiento_caja_chica) -> Dict:
        """
        Genera asiento por reposición de caja chica
        
        Args:
            movimiento_caja_chica: Instancia de MovimientoCajaChica
            
        Returns:
            Dict con el asiento
        """
        asiento = {
            'fecha': timezone.now(),
            'concepto': f'Reposición caja chica {movimiento_caja_chica.caja_chica.nombre}',
            'referencia': f'REP-CCH-{movimiento_caja_chica.id}',
            'tipo': 'REPOSICION_CAJA_CHICA',
            'movimientos': []
        }
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['CAJA_CHICA'],
            'tipo_movimiento': 'DEBE',
            'monto': movimiento_caja_chica.monto,
            'descripcion': f'Reposición {movimiento_caja_chica.caja_chica.nombre}'
        })
        
        asiento['movimientos'].append({
            'cuenta': AccountingService.CUENTAS['CAJA_EFECTIVO'],
            'tipo_movimiento': 'HABER',
            'monto': movimiento_caja_chica.monto,
            'descripcion': 'Efectivo para reposición de caja chica'
        })
        
        return asiento
    
    @staticmethod
    def _validar_balance(asiento: Dict) -> bool:
        """
        Valida que un asiento esté balanceado (DEBE = HABER)
        
        Args:
            asiento: Dict con el asiento
            
        Returns:
            bool: True si está balanceado
            
        Raises:
            ValueError: Si no está balanceado
        """
        total_debe = sum(
            m['monto'] for m in asiento['movimientos']
            if m['tipo_movimiento'] == 'DEBE'
        )
        
        total_haber = sum(
            m['monto'] for m in asiento['movimientos']
            if m['tipo_movimiento'] == 'HABER'
        )
        
        if total_debe != total_haber:
            raise ValueError(
                f"Asiento desbalanceado: DEBE={total_debe}, HABER={total_haber}"
            )
        
        return True
    
    @staticmethod
    def obtener_balance_general(fecha: Optional[datetime] = None) -> Dict:
        """
        Genera un balance general simplificado
        (Esto es un ejemplo básico - en producción sería más complejo)
        
        Args:
            fecha: Fecha del balance (por defecto hoy)
            
        Returns:
            Dict con el balance
        """
        if not fecha:
            fecha = timezone.now()
        
        # Este es un ejemplo simplificado
        # En producción, se consultarían los saldos reales de cada cuenta
        
        balance = {
            'fecha': fecha,
            'activos': {
                'circulante': {},
                'fijo': {},
                'total': Decimal('0.00')
            },
            'pasivos': {
                'circulante': {},
                'largo_plazo': {},
                'total': Decimal('0.00')
            },
            'patrimonio': {
                'capital': Decimal('0.00'),
                'utilidad': Decimal('0.00'),
                'total': Decimal('0.00')
            }
        }
        
        # Aquí se calcularían los saldos reales consultando movimientos
        # Este es solo un esqueleto de ejemplo
        
        return balance