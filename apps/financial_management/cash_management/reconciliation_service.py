# apps/financial_management/cash_management/reconciliation_service.py

"""
Servicio de conciliación y análisis de arqueos de caja
Detecta patrones, anomalías y genera reportes de diferencias
"""

from decimal import Decimal
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Tuple, Optional

from ..models import Caja, MovimientoCaja, ArqueoCaja


class ReconciliationService:
    """Servicio para conciliación y análisis de cajas"""
    
    @staticmethod
    def analizar_arqueo(arqueo: ArqueoCaja) -> Dict:
        """
        Analiza un arqueo y detecta posibles problemas
        
        Args:
            arqueo: Arqueo a analizar
            
        Returns:
            Dict con análisis completo
        """
        analisis = {
            'arqueo': arqueo,
            'estado': arqueo.estado,
            'diferencia': arqueo.diferencia,
            'diferencia_porcentaje': 0,
            'alertas': [],
            'observaciones': [],
            'es_critico': False
        }
        
        # Calcular porcentaje de diferencia
        if arqueo.monto_esperado > 0:
            analisis['diferencia_porcentaje'] = (
                abs(arqueo.diferencia) / arqueo.monto_esperado * 100
            )
        
        # Detectar alertas
        
        # 1. Diferencia significativa
        if abs(arqueo.diferencia) > Decimal('10.00'):
            analisis['alertas'].append({
                'tipo': 'DIFERENCIA_ALTA',
                'severidad': 'ALTA',
                'mensaje': f'Diferencia significativa de ${abs(arqueo.diferencia):.2f}'
            })
            analisis['es_critico'] = True
        
        # 2. Diferencia porcentual alta
        if analisis['diferencia_porcentaje'] > 2:
            analisis['alertas'].append({
                'tipo': 'DIFERENCIA_PORCENTUAL',
                'severidad': 'MEDIA',
                'mensaje': f'Diferencia del {analisis["diferencia_porcentaje"]:.2f}% respecto al esperado'
            })
        
        # 3. Sin explicación en diferencia crítica
        if abs(arqueo.diferencia) > Decimal('5.00') and not arqueo.observaciones_diferencia:
            analisis['alertas'].append({
                'tipo': 'SIN_EXPLICACION',
                'severidad': 'MEDIA',
                'mensaje': 'Diferencia sin explicación documentada'
            })
        
        # 4. Sesión muy larga
        duracion_sesion = arqueo.fecha_cierre - arqueo.fecha_apertura
        if duracion_sesion > timedelta(hours=12):
            analisis['alertas'].append({
                'tipo': 'SESION_LARGA',
                'severidad': 'BAJA',
                'mensaje': f'Sesión de {duracion_sesion.total_seconds() / 3600:.1f} horas'
            })
        
        # 5. Pocas ventas vs monto alto
        if arqueo.total_ventas > Decimal('1000.00'):
            movimientos_venta = MovimientoCaja.objects.filter(
                caja=arqueo.caja,
                tipo_movimiento='VENTA',
                fecha_movimiento__gte=arqueo.fecha_apertura,
                fecha_movimiento__lte=arqueo.fecha_cierre
            ).count()
            
            if movimientos_venta < 10:
                analisis['observaciones'].append(
                    f'Alto monto de ventas (${arqueo.total_ventas:.2f}) '
                    f'con pocas transacciones ({movimientos_venta})'
                )
        
        return analisis
    
    @staticmethod
    def comparar_con_historico(arqueo: ArqueoCaja) -> Dict:
        """
        Compara un arqueo con el histórico de la misma caja
        
        Args:
            arqueo: Arqueo a comparar
            
        Returns:
            Dict con comparación
        """
        # Obtener arqueos históricos de la misma caja (últimos 30)
        arqueos_historicos = ArqueoCaja.objects.filter(
            caja=arqueo.caja,
            fecha_cierre__lt=arqueo.fecha_cierre
        ).order_by('-fecha_cierre')[:30]
        
        if not arqueos_historicos.exists():
            return {
                'tiene_historico': False,
                'mensaje': 'Sin histórico para comparar'
            }
        
        # Calcular promedios
        promedios = arqueos_historicos.aggregate(
            promedio_ventas=Avg('total_ventas'),
            promedio_diferencia=Avg('diferencia'),
            promedio_ingresos=Avg('total_ingresos'),
            promedio_retiros=Avg('total_retiros')
        )
        
        comparacion = {
            'tiene_historico': True,
            'arqueos_analizados': arqueos_historicos.count(),
            'promedios': promedios,
            'variaciones': {},
            'anomalias': []
        }
        
        # Calcular variaciones
        comparacion['variaciones']['ventas'] = (
            ReconciliationService._calcular_variacion(
                arqueo.total_ventas,
                promedios['promedio_ventas']
            )
        )
        
        comparacion['variaciones']['diferencia'] = (
            ReconciliationService._calcular_variacion(
                abs(arqueo.diferencia),
                abs(promedios['promedio_diferencia'] or 0)
            )
        )
        
        # Detectar anomalías
        
        # Ventas muy por encima del promedio
        if comparacion['variaciones']['ventas'] > 50:
            comparacion['anomalias'].append({
                'tipo': 'VENTAS_ALTAS',
                'mensaje': f'Ventas {comparacion["variaciones"]["ventas"]:.1f}% '
                          f'por encima del promedio'
            })
        
        # Ventas muy por debajo del promedio
        elif comparacion['variaciones']['ventas'] < -50:
            comparacion['anomalias'].append({
                'tipo': 'VENTAS_BAJAS',
                'mensaje': f'Ventas {abs(comparacion["variaciones"]["ventas"]):.1f}% '
                          f'por debajo del promedio'
            })
        
        # Diferencia mayor al histórico
        if comparacion['variaciones']['diferencia'] > 100:
            comparacion['anomalias'].append({
                'tipo': 'DIFERENCIA_ANOMALA',
                'mensaje': 'Diferencia significativamente mayor al histórico'
            })
        
        return comparacion
    
    @staticmethod
    def generar_reporte_conciliacion(
        fecha_desde: timezone.datetime,
        fecha_hasta: timezone.datetime,
        caja: Optional[Caja] = None
    ) -> Dict:
        """
        Genera reporte completo de conciliación para un período
        
        Args:
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            caja: Caja específica (opcional)
            
        Returns:
            Dict con reporte completo
        """
        # Filtrar arqueos
        arqueos = ArqueoCaja.objects.filter(
            fecha_cierre__gte=fecha_desde,
            fecha_cierre__lte=fecha_hasta
        )
        
        if caja:
            arqueos = arqueos.filter(caja=caja)
        
        # Estadísticas generales
        totales = arqueos.aggregate(
            total_arqueos=Count('id'),
            total_ventas=Sum('total_ventas'),
            total_diferencias=Sum('diferencia'),
            promedio_diferencia=Avg('diferencia'),
            cuadrados=Count('id', filter=Q(estado='CUADRADO')),
            sobrantes=Count('id', filter=Q(estado='SOBRANTE')),
            faltantes=Count('id', filter=Q(estado='FALTANTE'))
        )
        
        reporte = {
            'periodo': {
                'desde': fecha_desde,
                'hasta': fecha_hasta
            },
            'caja': caja,
            'totales': totales,
            'porcentajes': {},
            'arqueos_problematicos': [],
            'resumen': {}
        }
        
        # Calcular porcentajes
        if totales['total_arqueos'] > 0:
            reporte['porcentajes']['cuadrados'] = (
                totales['cuadrados'] / totales['total_arqueos'] * 100
            )
            reporte['porcentajes']['con_diferencia'] = (
                (totales['sobrantes'] + totales['faltantes']) /
                totales['total_arqueos'] * 100
            )
        
        # Arqueos problemáticos (con diferencia > $5)
        arqueos_problematicos = arqueos.filter(
            diferencia__gt=Decimal('5.00')
        ) | arqueos.filter(
            diferencia__lt=Decimal('-5.00')
        )
        
        reporte['arqueos_problematicos'] = list(
            arqueos_problematicos.values(
                'numero_arqueo',
                'caja__nombre',
                'fecha_cierre',
                'diferencia',
                'estado',
                'usuario_cierre__first_name',
                'usuario_cierre__last_name'
            )
        )
        
        # Resumen
        reporte['resumen']['estado_general'] = (
            'BUENO' if reporte['porcentajes'].get('cuadrados', 0) >= 90 else
            'REGULAR' if reporte['porcentajes'].get('cuadrados', 0) >= 75 else
            'DEFICIENTE'
        )
        
        return reporte
    
    @staticmethod
    def detectar_patron_diferencias(caja: Caja, dias: int = 30) -> Dict:
        """
        Detecta patrones en las diferencias de una caja
        
        Args:
            caja: Caja a analizar
            dias: Días hacia atrás a analizar
            
        Returns:
            Dict con análisis de patrones
        """
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        arqueos = ArqueoCaja.objects.filter(
            caja=caja,
            fecha_cierre__gte=fecha_inicio
        ).order_by('fecha_cierre')
        
        if arqueos.count() < 5:
            return {
                'tiene_patron': False,
                'mensaje': 'Insuficientes arqueos para análisis de patrón'
            }
        
        # Análisis
        sobrantes_consecutivos = 0
        faltantes_consecutivos = 0
        max_sobrantes_consecutivos = 0
        max_faltantes_consecutivos = 0
        
        for arqueo in arqueos:
            if arqueo.estado == 'SOBRANTE':
                sobrantes_consecutivos += 1
                faltantes_consecutivos = 0
                max_sobrantes_consecutivos = max(
                    max_sobrantes_consecutivos,
                    sobrantes_consecutivos
                )
            elif arqueo.estado == 'FALTANTE':
                faltantes_consecutivos += 1
                sobrantes_consecutivos = 0
                max_faltantes_consecutivos = max(
                    max_faltantes_consecutivos,
                    faltantes_consecutivos
                )
            else:
                sobrantes_consecutivos = 0
                faltantes_consecutivos = 0
        
        analisis = {
            'tiene_patron': False,
            'tipo_patron': None,
            'detalles': {},
            'recomendaciones': []
        }
        
        # Detectar patrones
        if max_sobrantes_consecutivos >= 3:
            analisis['tiene_patron'] = True
            analisis['tipo_patron'] = 'SOBRANTES_RECURRENTES'
            analisis['detalles']['consecutivos'] = max_sobrantes_consecutivos
            analisis['recomendaciones'].append(
                'Revisar proceso de registro de ventas - '
                'posibles ventas no registradas'
            )
        
        if max_faltantes_consecutivos >= 3:
            analisis['tiene_patron'] = True
            analisis['tipo_patron'] = 'FALTANTES_RECURRENTES'
            analisis['detalles']['consecutivos'] = max_faltantes_consecutivos
            analisis['recomendaciones'].append(
                'Revisar procedimientos de manejo de efectivo - '
                'posible fuga o errores sistemáticos'
            )
        
        # Calcular promedio de diferencias
        promedio_diferencia = arqueos.aggregate(
            promedio=Avg('diferencia')
        )['promedio']
        
        if abs(promedio_diferencia or 0) > Decimal('2.00'):
            analisis['tiene_patron'] = True
            analisis['tipo_patron'] = analisis.get('tipo_patron') or 'DIFERENCIA_SISTEMATICA'
            analisis['detalles']['promedio_diferencia'] = float(promedio_diferencia)
            analisis['recomendaciones'].append(
                f'Diferencia promedio de ${abs(promedio_diferencia):.2f} - '
                'revisar procesos de apertura y cierre'
            )
        
        return analisis
    
    @staticmethod
    def _calcular_variacion(valor_actual: Decimal, valor_promedio: Decimal) -> float:
        """Calcula variación porcentual entre dos valores"""
        if valor_promedio == 0:
            return 0
        return float((valor_actual - valor_promedio) / valor_promedio * 100)
    
    @staticmethod
    def sugerir_acciones_correctivas(arqueo: ArqueoCaja) -> List[str]:
        """
        Sugiere acciones correctivas basadas en el arqueo
        
        Args:
            arqueo: Arqueo a analizar
            
        Returns:
            List de acciones recomendadas
        """
        acciones = []
        
        # Diferencia alta
        if abs(arqueo.diferencia) > Decimal('10.00'):
            acciones.append(
                'Realizar auditoría de movimientos de la sesión'
            )
            acciones.append(
                'Verificar tickets físicos vs registros del sistema'
            )
            acciones.append(
                'Revisar con el cajero responsable'
            )
        
        # Faltante
        if arqueo.estado == 'FALTANTE':
            acciones.append(
                'Buscar comprobantes no registrados'
            )
            acciones.append(
                'Verificar retiros autorizados'
            )
            acciones.append(
                'Revisar procedimientos de manejo de efectivo'
            )
        
        # Sobrante
        if arqueo.estado == 'SOBRANTE':
            acciones.append(
                'Revisar ventas que puedan no estar registradas'
            )
            acciones.append(
                'Verificar errores en digitación de montos'
            )
        
        # Sin explicación
        if abs(arqueo.diferencia) > Decimal('1.00') and not arqueo.observaciones_diferencia:
            acciones.append(
                'Documentar explicación de la diferencia'
            )
        
        return acciones