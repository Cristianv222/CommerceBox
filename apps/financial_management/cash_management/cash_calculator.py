# apps/financial_management/cash_management/cash_calculator.py

"""
Calculadora de efectivo y utilidades financieras
Realiza cálculos complejos relacionados con manejo de efectivo
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class CashCalculator:
    """Calculadora de efectivo y operaciones financieras"""
    
    # Denominaciones estándar de efectivo
    DENOMINACIONES = {
        'billetes_100': Decimal('100.00'),
        'billetes_50': Decimal('50.00'),
        'billetes_20': Decimal('20.00'),
        'billetes_10': Decimal('10.00'),
        'billetes_5': Decimal('5.00'),
        'billetes_1': Decimal('1.00'),
    }
    
    @staticmethod
    def calcular_total_efectivo(desglose: Dict[str, int]) -> Decimal:
        """
        Calcula el total de efectivo según desglose de billetes
        
        Args:
            desglose: Dict con cantidad de cada denominación
            Ejemplo: {
                'billetes_100': 5,
                'billetes_50': 10,
                'billetes_20': 20,
                'monedas': Decimal('15.50')
            }
            
        Returns:
            Decimal: Total calculado
        """
        total = Decimal('0.00')
        
        # Sumar billetes
        for nombre, valor in CashCalculator.DENOMINACIONES.items():
            cantidad = desglose.get(nombre, 0)
            total += Decimal(str(cantidad)) * valor
        
        # Sumar monedas
        monedas = desglose.get('monedas', Decimal('0.00'))
        if isinstance(monedas, (int, float)):
            monedas = Decimal(str(monedas))
        total += monedas
        
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def sugerir_desglose(monto: Decimal) -> Dict[str, int]:
        """
        Sugiere un desglose óptimo de billetes para un monto dado
        
        Args:
            monto: Monto a desglosar
            
        Returns:
            Dict con sugerencia de billetes
        """
        monto_restante = monto
        desglose = {}
        
        # Ordenar denominaciones de mayor a menor
        denominaciones_ordenadas = sorted(
            CashCalculator.DENOMINACIONES.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for nombre, valor in denominaciones_ordenadas:
            if monto_restante >= valor:
                cantidad = int(monto_restante / valor)
                desglose[nombre] = cantidad
                monto_restante -= cantidad * valor
            else:
                desglose[nombre] = 0
        
        # Lo que queda va como monedas
        if monto_restante > 0:
            desglose['monedas'] = monto_restante.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )
        else:
            desglose['monedas'] = Decimal('0.00')
        
        return desglose
    
    @staticmethod
    def calcular_cambio(monto_pago: Decimal, monto_total: Decimal) -> Decimal:
        """
        Calcula el cambio a devolver
        
        Args:
            monto_pago: Monto con el que paga el cliente
            monto_total: Total de la compra
            
        Returns:
            Decimal: Cambio a devolver
            
        Raises:
            ValueError: Si el pago es insuficiente
        """
        if monto_pago < monto_total:
            raise ValueError(
                f"Pago insuficiente. Se necesita ${monto_total:.2f}, "
                f"se recibió ${monto_pago:.2f}"
            )
        
        cambio = monto_pago - monto_total
        return cambio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def desglosar_cambio(cambio: Decimal) -> Dict[str, int]:
        """
        Sugiere cómo dar el cambio con las menores denominaciones posibles
        
        Args:
            cambio: Monto del cambio
            
        Returns:
            Dict con desglose del cambio
        """
        return CashCalculator.sugerir_desglose(cambio)
    
    @staticmethod
    def validar_monto_apertura(
        monto: Decimal,
        minimo: Decimal = Decimal('100.00'),
        maximo: Decimal = Decimal('1000.00')
    ) -> Tuple[bool, str]:
        """
        Valida que el monto de apertura esté en rangos aceptables
        
        Args:
            monto: Monto a validar
            minimo: Monto mínimo permitido
            maximo: Monto máximo permitido
            
        Returns:
            Tuple[bool, str]: (es_válido, mensaje)
        """
        if monto < Decimal('0.00'):
            return False, "El monto no puede ser negativo"
        
        if monto < minimo:
            return False, f"El monto mínimo de apertura es ${minimo:.2f}"
        
        if monto > maximo:
            return False, f"El monto máximo de apertura es ${maximo:.2f}"
        
        return True, "Monto válido"
    
    @staticmethod
    def calcular_vuelto_aproximado(cambio: Decimal) -> Decimal:
        """
        Redondea el cambio al múltiplo de 5 centavos más cercano
        (útil en países donde no circulan centavos pequeños)
        
        Args:
            cambio: Cambio calculado
            
        Returns:
            Decimal: Cambio redondeado
        """
        # Redondear a múltiplo de 0.05
        factor = Decimal('0.05')
        return (cambio / factor).quantize(
            Decimal('1'),
            rounding=ROUND_HALF_UP
        ) * factor
    
    @staticmethod
    def calcular_porcentaje_comision(
        monto: Decimal,
        porcentaje: Decimal
    ) -> Decimal:
        """
        Calcula comisión sobre un monto
        
        Args:
            monto: Monto base
            porcentaje: Porcentaje de comisión (ej: 2.5 para 2.5%)
            
        Returns:
            Decimal: Monto de la comisión
        """
        comision = monto * (porcentaje / Decimal('100'))
        return comision.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calcular_efectivo_final_esperado(
        monto_apertura: Decimal,
        total_ingresos: Decimal,
        total_retiros: Decimal
    ) -> Decimal:
        """
        Calcula el efectivo final esperado en caja
        
        Args:
            monto_apertura: Monto inicial
            total_ingresos: Total de ingresos (ventas + otros ingresos)
            total_retiros: Total de retiros
            
        Returns:
            Decimal: Efectivo esperado al cierre
        """
        esperado = monto_apertura + total_ingresos - total_retiros
        return esperado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def analizar_diferencia(
        monto_esperado: Decimal,
        monto_contado: Decimal
    ) -> Dict:
        """
        Analiza la diferencia entre esperado y contado
        
        Args:
            monto_esperado: Lo que debería haber
            monto_contado: Lo que realmente hay
            
        Returns:
            Dict con análisis detallado
        """
        diferencia = monto_contado - monto_esperado
        abs_diferencia = abs(diferencia)
        
        # Clasificar severidad
        if abs_diferencia == 0:
            severidad = 'NINGUNA'
            color = 'green'
        elif abs_diferencia <= Decimal('1.00'):
            severidad = 'MINIMA'
            color = 'blue'
        elif abs_diferencia <= Decimal('5.00'):
            severidad = 'BAJA'
            color = 'yellow'
        elif abs_diferencia <= Decimal('10.00'):
            severidad = 'MEDIA'
            color = 'orange'
        else:
            severidad = 'ALTA'
            color = 'red'
        
        # Calcular porcentaje
        if monto_esperado > 0:
            porcentaje = (abs_diferencia / monto_esperado * 100)
        else:
            porcentaje = Decimal('0.00')
        
        return {
            'diferencia': diferencia,
            'abs_diferencia': abs_diferencia,
            'tipo': 'SOBRANTE' if diferencia > 0 else 'FALTANTE' if diferencia < 0 else 'CUADRADO',
            'severidad': severidad,
            'color': color,
            'porcentaje': porcentaje,
            'requiere_justificacion': abs_diferencia > Decimal('1.00'),
            'es_aceptable': abs_diferencia <= Decimal('1.00')
        }
    
    @staticmethod
    def calcular_promedio_movil(valores: List[Decimal], periodo: int = 7) -> Decimal:
        """
        Calcula promedio móvil de una serie de valores
        Útil para análisis de tendencias
        
        Args:
            valores: Lista de valores
            periodo: Cantidad de valores a promediar
            
        Returns:
            Decimal: Promedio móvil
        """
        if not valores:
            return Decimal('0.00')
        
        valores_periodo = valores[-periodo:] if len(valores) >= periodo else valores
        
        if not valores_periodo:
            return Decimal('0.00')
        
        total = sum(valores_periodo)
        promedio = total / len(valores_periodo)
        
        return promedio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def proyectar_cierre(
        monto_actual: Decimal,
        promedio_venta_hora: Decimal,
        horas_restantes: float
    ) -> Dict:
        """
        Proyecta el cierre de caja basado en promedios
        
        Args:
            monto_actual: Efectivo actual en caja
            promedio_venta_hora: Promedio de ventas por hora
            horas_restantes: Horas hasta el cierre
            
        Returns:
            Dict con proyección
        """
        ventas_proyectadas = promedio_venta_hora * Decimal(str(horas_restantes))
        cierre_proyectado = monto_actual + ventas_proyectadas
        
        return {
            'monto_actual': monto_actual,
            'ventas_proyectadas': ventas_proyectadas.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'cierre_proyectado': cierre_proyectado.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'horas_restantes': horas_restantes
        }
    
    @staticmethod
    def calcular_fondo_caja_chica_optimo(
        gasto_promedio_diario: Decimal,
        dias_reposicion: int = 7
    ) -> Decimal:
        """
        Calcula el fondo óptimo para caja chica
        
        Args:
            gasto_promedio_diario: Gasto promedio por día
            dias_reposicion: Días entre reposiciones
            
        Returns:
            Decimal: Fondo recomendado
        """
        # Calcular para el período + 20% de margen
        fondo_base = gasto_promedio_diario * dias_reposicion
        margen = fondo_base * Decimal('0.20')
        fondo_optimo = fondo_base + margen
        
        # Redondear a múltiplo de 50 para facilitar manejo
        factor = Decimal('50.00')
        return (fondo_optimo / factor).quantize(
            Decimal('1'),
            rounding=ROUND_HALF_UP
        ) * factor
    
    @staticmethod
    def dividir_pago_multiple(
        total: Decimal,
        formas_pago: Dict[str, Decimal]
    ) -> Tuple[bool, Dict, str]:
        """
        Valida y procesa pagos con múltiples formas de pago
        
        Args:
            total: Total a pagar
            formas_pago: Dict con monto por cada forma
            Ejemplo: {
                'efectivo': Decimal('50.00'),
                'tarjeta': Decimal('30.00')
            }
            
        Returns:
            Tuple[bool, Dict, str]: (válido, detalle, mensaje)
        """
        total_pagado = sum(formas_pago.values())
        diferencia = total_pagado - total
        
        if diferencia < 0:
            return False, {}, f"Falta pagar ${abs(diferencia):.2f}"
        
        # Preparar detalle
        detalle = {
            'total': total,
            'total_pagado': total_pagado,
            'cambio': diferencia,
            'formas_pago': formas_pago
        }
        
        if diferencia > 0:
            mensaje = f"Pago completo. Cambio: ${diferencia:.2f}"
        else:
            mensaje = "Pago exacto"
        
        return True, detalle, mensaje
    
    @staticmethod
    def formatear_dinero(monto: Decimal, incluir_signo: bool = True) -> str:
        """
        Formatea un monto de dinero para visualización
        
        Args:
            monto: Monto a formatear
            incluir_signo: Si incluir el símbolo $
            
        Returns:
            str: Monto formateado
        """
        monto_formateado = f"{monto:,.2f}"
        
        if incluir_signo:
            return f"${monto_formateado}"
        
        return monto_formateado