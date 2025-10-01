# apps/financial_management/accounting/cost_calculator.py

"""
Calculador de costos y análisis de rentabilidad
Calcula márgenes, puntos de equilibrio y análisis financiero
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple


class CostCalculator:
    """Calculador de costos y rentabilidad"""
    
    @staticmethod
    def calcular_margen_ganancia(
        precio_venta: Decimal,
        costo: Decimal
    ) -> Dict:
        """
        Calcula el margen de ganancia
        
        Args:
            precio_venta: Precio de venta
            costo: Costo del producto
            
        Returns:
            Dict con análisis de margen
        """
        utilidad = precio_venta - costo
        
        if precio_venta > 0:
            margen_porcentaje = (utilidad / precio_venta) * 100
        else:
            margen_porcentaje = Decimal('0.00')
        
        if costo > 0:
            markup_porcentaje = (utilidad / costo) * 100
        else:
            markup_porcentaje = Decimal('0.00')
        
        return {
            'precio_venta': precio_venta,
            'costo': costo,
            'utilidad': utilidad,
            'margen_porcentaje': margen_porcentaje.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'markup_porcentaje': markup_porcentaje.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'es_rentable': utilidad > 0
        }
    
    @staticmethod
    def calcular_precio_desde_margen(
        costo: Decimal,
        margen_deseado: Decimal
    ) -> Decimal:
        """
        Calcula el precio de venta necesario para lograr un margen
        
        Args:
            costo: Costo del producto
            margen_deseado: Margen deseado en porcentaje (ej: 30 para 30%)
            
        Returns:
            Decimal: Precio de venta recomendado
        """
        # Precio = Costo / (1 - Margen/100)
        divisor = 1 - (margen_deseado / 100)
        
        if divisor <= 0:
            raise ValueError("Margen inválido")
        
        precio = costo / divisor
        return precio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calcular_precio_desde_markup(
        costo: Decimal,
        markup_deseado: Decimal
    ) -> Decimal:
        """
        Calcula precio desde markup sobre el costo
        
        Args:
            costo: Costo del producto
            markup_deseado: Markup en porcentaje (ej: 50 para 50% sobre costo)
            
        Returns:
            Decimal: Precio de venta
        """
        # Precio = Costo × (1 + Markup/100)
        precio = costo * (1 + markup_deseado / 100)
        return precio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calcular_punto_equilibrio(
        costos_fijos: Decimal,
        precio_unitario: Decimal,
        costo_variable_unitario: Decimal
    ) -> Dict:
        """
        Calcula el punto de equilibrio
        
        Args:
            costos_fijos: Costos fijos totales
            precio_unitario: Precio de venta por unidad
            costo_variable_unitario: Costo variable por unidad
            
        Returns:
            Dict con análisis de punto de equilibrio
        """
        margen_contribucion = precio_unitario - costo_variable_unitario
        
        if margen_contribucion <= 0:
            return {
                'error': 'El margen de contribución debe ser positivo',
                'es_viable': False
            }
        
        # Unidades necesarias para cubrir costos fijos
        unidades_equilibrio = costos_fijos / margen_contribucion
        
        # Ventas en dinero necesarias
        ventas_equilibrio = unidades_equilibrio * precio_unitario
        
        # Ratio de margen de contribución
        ratio_margen = (margen_contribucion / precio_unitario) * 100
        
        return {
            'costos_fijos': costos_fijos,
            'precio_unitario': precio_unitario,
            'costo_variable_unitario': costo_variable_unitario,
            'margen_contribucion': margen_contribucion,
            'ratio_margen_contribucion': ratio_margen.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'unidades_equilibrio': unidades_equilibrio.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'ventas_equilibrio': ventas_equilibrio.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'es_viable': margen_contribucion > 0
        }
    
    @staticmethod
    def calcular_roi(
        inversion_inicial: Decimal,
        ganancia_neta: Decimal,
        periodo_meses: int = 12
    ) -> Dict:
        """
        Calcula el Retorno de Inversión (ROI)
        
        Args:
            inversion_inicial: Inversión inicial
            ganancia_neta: Ganancia neta obtenida
            periodo_meses: Período en meses
            
        Returns:
            Dict con análisis de ROI
        """
        if inversion_inicial == 0:
            return {'error': 'La inversión inicial no puede ser cero'}
        
        # ROI = (Ganancia Neta / Inversión Inicial) × 100
        roi = (ganancia_neta / inversion_inicial) * 100
        
        # ROI anualizado
        if periodo_meses > 0:
            roi_anualizado = roi * (12 / periodo_meses)
        else:
            roi_anualizado = Decimal('0.00')
        
        # Meses para recuperar inversión
        if ganancia_neta > 0:
            ganancia_mensual = ganancia_neta / periodo_meses
            meses_recuperacion = inversion_inicial / ganancia_mensual
        else:
            meses_recuperacion = Decimal('999.99')  # Infinito prácticamente
        
        return {
            'inversion_inicial': inversion_inicial,
            'ganancia_neta': ganancia_neta,
            'periodo_meses': periodo_meses,
            'roi_porcentaje': roi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'roi_anualizado': roi_anualizado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'meses_recuperacion': meses_recuperacion.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'es_rentable': roi > 0
        }
    
    @staticmethod
    def analizar_rentabilidad_producto(
        ventas_unidades: int,
        precio_venta: Decimal,
        costo_unitario: Decimal,
        costos_asociados: Decimal = Decimal('0.00')
    ) -> Dict:
        """
        Analiza la rentabilidad de un producto
        
        Args:
            ventas_unidades: Unidades vendidas
            precio_venta: Precio de venta unitario
            costo_unitario: Costo unitario
            costos_asociados: Costos adicionales asociados
            
        Returns:
            Dict con análisis completo
        """
        ventas_totales = Decimal(ventas_unidades) * precio_venta
        costos_totales = (Decimal(ventas_unidades) * costo_unitario) + costos_asociados
        utilidad_total = ventas_totales - costos_totales
        utilidad_unitaria = precio_venta - costo_unitario
        
        if ventas_totales > 0:
            margen_porcentaje = (utilidad_total / ventas_totales) * 100
        else:
            margen_porcentaje = Decimal('0.00')
        
        return {
            'ventas': {
                'unidades': ventas_unidades,
                'precio_unitario': precio_venta,
                'total': ventas_totales
            },
            'costos': {
                'costo_unitario': costo_unitario,
                'costos_asociados': costos_asociados,
                'total': costos_totales
            },
            'utilidad': {
                'unitaria': utilidad_unitaria,
                'total': utilidad_total,
                'margen_porcentaje': margen_porcentaje.quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP
                )
            },
            'es_rentable': utilidad_total > 0
        }
    
    @staticmethod
    def calcular_costo_promedio_ponderado(
        compras: List[Dict]
    ) -> Decimal:
        """
        Calcula el costo promedio ponderado (WAC - Weighted Average Cost)
        
        Args:
            compras: Lista de compras con 'cantidad' y 'costo_unitario'
            Ejemplo: [
                {'cantidad': 10, 'costo_unitario': Decimal('5.00')},
                {'cantidad': 20, 'costo_unitario': Decimal('6.00')}
            ]
            
        Returns:
            Decimal: Costo promedio ponderado
        """
        if not compras:
            return Decimal('0.00')
        
        total_costo = Decimal('0.00')
        total_unidades = 0
        
        for compra in compras:
            cantidad = Decimal(str(compra['cantidad']))
            costo = compra['costo_unitario']
            total_costo += cantidad * costo
            total_unidades += compra['cantidad']
        
        if total_unidades == 0:
            return Decimal('0.00')
        
        promedio = total_costo / Decimal(str(total_unidades))
        return promedio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def proyectar_utilidad(
        ventas_proyectadas: Decimal,
        margen_promedio: Decimal,
        gastos_fijos: Decimal
    ) -> Dict:
        """
        Proyecta la utilidad esperada
        
        Args:
            ventas_proyectadas: Ventas proyectadas
            margen_promedio: Margen de ganancia promedio (%)
            gastos_fijos: Gastos fijos del período
            
        Returns:
            Dict con proyección
        """
        utilidad_bruta = ventas_proyectadas * (margen_promedio / 100)
        utilidad_neta = utilidad_bruta - gastos_fijos
        
        if ventas_proyectadas > 0:
            margen_neto = (utilidad_neta / ventas_proyectadas) * 100
        else:
            margen_neto = Decimal('0.00')
        
        return {
            'ventas_proyectadas': ventas_proyectadas,
            'margen_bruto_porcentaje': margen_promedio,
            'utilidad_bruta': utilidad_bruta.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'gastos_fijos': gastos_fijos,
            'utilidad_neta': utilidad_neta.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'margen_neto_porcentaje': margen_neto.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'es_rentable': utilidad_neta > 0
        }
    
    @staticmethod
    def calcular_ratios_financieros(
        activos_corrientes: Decimal,
        pasivos_corrientes: Decimal,
        inventario: Decimal,
        ventas: Decimal,
        utilidad_neta: Decimal,
        patrimonio: Decimal
    ) -> Dict:
        """
        Calcula ratios financieros principales
        
        Args:
            activos_corrientes: Activos corrientes
            pasivos_corrientes: Pasivos corrientes
            inventario: Valor del inventario
            ventas: Ventas del período
            utilidad_neta: Utilidad neta
            patrimonio: Patrimonio
            
        Returns:
            Dict con ratios calculados
        """
        ratios = {}
        
        # Ratio de Liquidez Corriente
        if pasivos_corrientes > 0:
            ratios['liquidez_corriente'] = (
                activos_corrientes / pasivos_corrientes
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            ratios['liquidez_corriente'] = Decimal('0.00')
        
        # Prueba Ácida (sin inventario)
        if pasivos_corrientes > 0:
            activos_liquidos = activos_corrientes - inventario
            ratios['prueba_acida'] = (
                activos_liquidos / pasivos_corrientes
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            ratios['prueba_acida'] = Decimal('0.00')
        
        # ROE (Return on Equity)
        if patrimonio > 0:
            ratios['roe_porcentaje'] = (
                (utilidad_neta / patrimonio) * 100
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            ratios['roe_porcentaje'] = Decimal('0.00')
        
        # Margen Neto de Ventas
        if ventas > 0:
            ratios['margen_neto_porcentaje'] = (
                (utilidad_neta / ventas) * 100
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            ratios['margen_neto_porcentaje'] = Decimal('0.00')
        
        # Interpretaciones
        ratios['interpretacion'] = {
            'liquidez': 'Buena' if ratios['liquidez_corriente'] >= Decimal('2.00') else 'Regular' if ratios['liquidez_corriente'] >= Decimal('1.00') else 'Baja',
            'solvencia': 'Buena' if ratios['prueba_acida'] >= Decimal('1.00') else 'Requiere atención',
            'rentabilidad': 'Buena' if ratios['roe_porcentaje'] >= Decimal('15.00') else 'Regular' if ratios['roe_porcentaje'] >= Decimal('10.00') else 'Baja'
        }
        
        return ratios
    
    @staticmethod
    def analizar_estructura_costos(
        costos_fijos: Decimal,
        costos_variables: Decimal,
        ventas: Decimal
    ) -> Dict:
        """
        Analiza la estructura de costos del negocio
        
        Args:
            costos_fijos: Costos fijos totales
            costos_variables: Costos variables totales
            ventas: Ventas totales
            
        Returns:
            Dict con análisis
        """
        costos_totales = costos_fijos + costos_variables
        
        if costos_totales > 0:
            proporcion_fijos = (costos_fijos / costos_totales) * 100
            proporcion_variables = (costos_variables / costos_totales) * 100
        else:
            proporcion_fijos = Decimal('0.00')
            proporcion_variables = Decimal('0.00')
        
        # Apalancamiento operativo
        if costos_variables > 0:
            margen_contribucion = ventas - costos_variables
            if margen_contribucion - costos_fijos != 0:
                apalancamiento = margen_contribucion / (margen_contribucion - costos_fijos)
            else:
                apalancamiento = Decimal('0.00')
        else:
            apalancamiento = Decimal('0.00')
        
        return {
            'costos_fijos': costos_fijos,
            'costos_variables': costos_variables,
            'costos_totales': costos_totales,
            'proporcion_fijos_porcentaje': proporcion_fijos.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'proporcion_variables_porcentaje': proporcion_variables.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'apalancamiento_operativo': apalancamiento.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            ),
            'recomendacion': (
                'Estructura flexible' if proporcion_variables > 60 else
                'Estructura balanceada' if proporcion_variables > 40 else
                'Estructura rígida - alto riesgo operativo'
            )
        }