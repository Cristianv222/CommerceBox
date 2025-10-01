# apps/financial_management/accounting/entry_generator.py

"""
Generador automático de asientos contables
Crea registros contables formateados y listos para exportar
"""

from decimal import Decimal
from django.utils import timezone
from typing import Dict, List
from datetime import datetime
import json


class EntryGenerator:
    """Generador de asientos contables en diferentes formatos"""
    
    @staticmethod
    def generar_libro_diario(
        fecha_desde: datetime,
        fecha_hasta: datetime,
        incluir_detalles: bool = True
    ) -> List[Dict]:
        """
        Genera el libro diario para un período
        
        Args:
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            incluir_detalles: Si incluir detalles de cada asiento
            
        Returns:
            List de asientos del período
        """
        from ..models import MovimientoCaja, MovimientoCajaChica
        from .accounting_service import AccountingService
        
        asientos = []
        
        # Obtener movimientos de caja
        movimientos_caja = MovimientoCaja.objects.filter(
            fecha_movimiento__gte=fecha_desde,
            fecha_movimiento__lte=fecha_hasta
        ).select_related('caja', 'usuario', 'venta').order_by('fecha_movimiento')
        
        for movimiento in movimientos_caja:
            if movimiento.venta:
                # Generar asiento de venta
                asiento = AccountingService.generar_asiento_venta(
                    movimiento.venta,
                    metodo_pago='EFECTIVO'
                )
                asientos.append(asiento)
        
        # Obtener movimientos de caja chica
        movimientos_caja_chica = MovimientoCajaChica.objects.filter(
            fecha_movimiento__gte=fecha_desde,
            fecha_movimiento__lte=fecha_hasta,
            tipo_movimiento='GASTO'
        ).select_related('caja_chica', 'usuario').order_by('fecha_movimiento')
        
        for movimiento in movimientos_caja_chica:
            asiento = AccountingService.generar_asiento_gasto_caja_chica(movimiento)
            asientos.append(asiento)
        
        return asientos
    
    @staticmethod
    def formatear_asiento_texto(asiento: Dict) -> str:
        """
        Formatea un asiento para visualización en texto
        
        Args:
            asiento: Dict con el asiento
            
        Returns:
            str: Asiento formateado
        """
        lineas = []
        lineas.append("=" * 80)
        lineas.append(f"ASIENTO CONTABLE")
        lineas.append(f"Fecha: {asiento['fecha'].strftime('%d/%m/%Y %H:%M')}")
        lineas.append(f"Concepto: {asiento['concepto']}")
        lineas.append(f"Referencia: {asiento['referencia']}")
        lineas.append("=" * 80)
        lineas.append("")
        lineas.append(f"{'CUENTA':<50} {'DEBE':>12} {'HABER':>12}")
        lineas.append("-" * 80)
        
        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')
        
        for mov in asiento['movimientos']:
            cuenta_nombre = f"{mov['cuenta']['codigo']} - {mov['cuenta']['nombre']}"
            debe = mov['monto'] if mov['tipo_movimiento'] == 'DEBE' else Decimal('0.00')
            haber = mov['monto'] if mov['tipo_movimiento'] == 'HABER' else Decimal('0.00')
            
            total_debe += debe
            total_haber += haber
            
            lineas.append(
                f"{cuenta_nombre:<50} "
                f"{debe:>12.2f} "
                f"{haber:>12.2f}"
            )
        
        lineas.append("-" * 80)
        lineas.append(
            f"{'TOTALES':<50} "
            f"{total_debe:>12.2f} "
            f"{total_haber:>12.2f}"
        )
        lineas.append("=" * 80)
        
        return "\n".join(lineas)
    
    @staticmethod
    def exportar_a_excel_format(asientos: List[Dict]) -> List[Dict]:
        """
        Convierte asientos a formato para exportar a Excel
        
        Args:
            asientos: Lista de asientos
            
        Returns:
            List de dicts en formato tabla
        """
        filas = []
        
        for asiento in asientos:
            for mov in asiento['movimientos']:
                filas.append({
                    'Fecha': asiento['fecha'].strftime('%d/%m/%Y'),
                    'Referencia': asiento['referencia'],
                    'Concepto': asiento['concepto'],
                    'Código Cuenta': mov['cuenta']['codigo'],
                    'Nombre Cuenta': mov['cuenta']['nombre'],
                    'Debe': float(mov['monto']) if mov['tipo_movimiento'] == 'DEBE' else 0,
                    'Haber': float(mov['monto']) if mov['tipo_movimiento'] == 'HABER' else 0,
                })
        
        return filas
    
    @staticmethod
    def exportar_a_json(asientos: List[Dict]) -> str:
        """
        Exporta asientos a formato JSON
        
        Args:
            asientos: Lista de asientos
            
        Returns:
            str: JSON formateado
        """
        # Convertir Decimal a float para serialización
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError
        
        return json.dumps(asientos, indent=2, default=decimal_default)
    
    @staticmethod
    def generar_mayor_cuenta(
        codigo_cuenta: str,
        fecha_desde: datetime,
        fecha_hasta: datetime
    ) -> Dict:
        """
        Genera el libro mayor para una cuenta específica
        
        Args:
            codigo_cuenta: Código de la cuenta
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            
        Returns:
            Dict con movimientos de la cuenta
        """
        from .accounting_service import AccountingService
        
        # Buscar la cuenta
        cuenta = None
        for key, value in AccountingService.CUENTAS.items():
            if value['codigo'] == codigo_cuenta:
                cuenta = value
                break
        
        if not cuenta:
            return {'error': f'Cuenta {codigo_cuenta} no encontrada'}
        
        # Obtener todos los asientos del período
        asientos = EntryGenerator.generar_libro_diario(
            fecha_desde,
            fecha_hasta,
            incluir_detalles=True
        )
        
        # Filtrar movimientos de esta cuenta
        movimientos_cuenta = []
        saldo = Decimal('0.00')
        
        for asiento in asientos:
            for mov in asiento['movimientos']:
                if mov['cuenta']['codigo'] == codigo_cuenta:
                    # Calcular saldo según tipo de cuenta
                    if cuenta['tipo'] in ['ACTIVO', 'GASTO', 'COSTO']:
                        # Aumenta con DEBE, disminuye con HABER
                        if mov['tipo_movimiento'] == 'DEBE':
                            saldo += mov['monto']
                        else:
                            saldo -= mov['monto']
                    else:  # PASIVO, PATRIMONIO, INGRESO
                        # Aumenta con HABER, disminuye con DEBE
                        if mov['tipo_movimiento'] == 'HABER':
                            saldo += mov['monto']
                        else:
                            saldo -= mov['monto']
                    
                    movimientos_cuenta.append({
                        'fecha': asiento['fecha'],
                        'referencia': asiento['referencia'],
                        'concepto': asiento['concepto'],
                        'debe': mov['monto'] if mov['tipo_movimiento'] == 'DEBE' else Decimal('0.00'),
                        'haber': mov['monto'] if mov['tipo_movimiento'] == 'HABER' else Decimal('0.00'),
                        'saldo': saldo
                    })
        
        return {
            'cuenta': cuenta,
            'periodo': {
                'desde': fecha_desde,
                'hasta': fecha_hasta
            },
            'movimientos': movimientos_cuenta,
            'saldo_final': saldo
        }
    
    @staticmethod
    def generar_balance_comprobacion(
        fecha_desde: datetime,
        fecha_hasta: datetime
    ) -> Dict:
        """
        Genera balance de comprobación del período
        
        Args:
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            
        Returns:
            Dict con balance de comprobación
        """
        from .accounting_service import AccountingService
        
        # Obtener todos los asientos
        asientos = EntryGenerator.generar_libro_diario(
            fecha_desde,
            fecha_hasta
        )
        
        # Acumular por cuenta
        saldos_cuentas = {}
        
        for asiento in asientos:
            for mov in asiento['movimientos']:
                codigo = mov['cuenta']['codigo']
                
                if codigo not in saldos_cuentas:
                    saldos_cuentas[codigo] = {
                        'cuenta': mov['cuenta'],
                        'debe': Decimal('0.00'),
                        'haber': Decimal('0.00'),
                        'saldo': Decimal('0.00')
                    }
                
                if mov['tipo_movimiento'] == 'DEBE':
                    saldos_cuentas[codigo]['debe'] += mov['monto']
                else:
                    saldos_cuentas[codigo]['haber'] += mov['monto']
        
        # Calcular saldos
        for codigo, datos in saldos_cuentas.items():
            tipo_cuenta = datos['cuenta']['tipo']
            
            if tipo_cuenta in ['ACTIVO', 'GASTO', 'COSTO']:
                datos['saldo'] = datos['debe'] - datos['haber']
            else:  # PASIVO, PATRIMONIO, INGRESO
                datos['saldo'] = datos['haber'] - datos['debe']
        
        # Calcular totales
        total_debe = sum(d['debe'] for d in saldos_cuentas.values())
        total_haber = sum(d['haber'] for d in saldos_cuentas.values())
        
        return {
            'periodo': {
                'desde': fecha_desde,
                'hasta': fecha_hasta
            },
            'cuentas': list(saldos_cuentas.values()),
            'totales': {
                'debe': total_debe,
                'haber': total_haber,
                'balanceado': total_debe == total_haber
            }
        }
    
    @staticmethod
    def generar_estado_resultados(
        fecha_desde: datetime,
        fecha_hasta: datetime
    ) -> Dict:
        """
        Genera estado de resultados (P&L) del período
        
        Args:
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            
        Returns:
            Dict con estado de resultados
        """
        balance = EntryGenerator.generar_balance_comprobacion(
            fecha_desde,
            fecha_hasta
        )
        
        # Separar por tipo
        ingresos = Decimal('0.00')
        costos = Decimal('0.00')
        gastos = Decimal('0.00')
        
        for cuenta in balance['cuentas']:
            tipo = cuenta['cuenta']['tipo']
            saldo = abs(cuenta['saldo'])
            
            if tipo == 'INGRESO':
                ingresos += saldo
            elif tipo == 'COSTO':
                costos += saldo
            elif tipo == 'GASTO':
                gastos += saldo
        
        # Calcular resultados
        utilidad_bruta = ingresos - costos
        utilidad_neta = utilidad_bruta - gastos
        
        return {
            'periodo': balance['periodo'],
            'ingresos': ingresos,
            'costos': costos,
            'utilidad_bruta': utilidad_bruta,
            'gastos': gastos,
            'utilidad_neta': utilidad_neta,
            'margen_bruto_porcentaje': (
                (utilidad_bruta / ingresos * 100) if ingresos > 0 else Decimal('0.00')
            ),
            'margen_neto_porcentaje': (
                (utilidad_neta / ingresos * 100) if ingresos > 0 else Decimal('0.00')
            )
        }
    
    @staticmethod
    def formatear_estado_resultados_texto(estado_resultados: Dict) -> str:
        """
        Formatea estado de resultados para visualización
        
        Args:
            estado_resultados: Dict con estado de resultados
            
        Returns:
            str: Estado formateado
        """
        er = estado_resultados
        lineas = []
        
        lineas.append("=" * 60)
        lineas.append("ESTADO DE RESULTADOS")
        lineas.append(f"Del {er['periodo']['desde'].strftime('%d/%m/%Y')} "
                     f"al {er['periodo']['hasta'].strftime('%d/%m/%Y')}")
        lineas.append("=" * 60)
        lineas.append("")
        
        lineas.append(f"{'INGRESOS':<40} ${er['ingresos']:>15,.2f}")
        lineas.append(f"{'(-) Costo de Ventas':<40} ${er['costos']:>15,.2f}")
        lineas.append("-" * 60)
        lineas.append(f"{'UTILIDAD BRUTA':<40} ${er['utilidad_bruta']:>15,.2f}")
        lineas.append(f"{'Margen Bruto':<40} {er['margen_bruto_porcentaje']:>15.2f}%")
        lineas.append("")
        
        lineas.append(f"{'(-) Gastos Operativos':<40} ${er['gastos']:>15,.2f}")
        lineas.append("=" * 60)
        lineas.append(f"{'UTILIDAD NETA':<40} ${er['utilidad_neta']:>15,.2f}")
        lineas.append(f"{'Margen Neto':<40} {er['margen_neto_porcentaje']:>15.2f}%")
        lineas.append("=" * 60)
        
        return "\n".join(lineas)