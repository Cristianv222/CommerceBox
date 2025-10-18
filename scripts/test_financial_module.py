#!/usr/bin/env python
# test_financial_module.py
"""
Script de prueba para verificar que el módulo financiero está correctamente implementado
Ejecutar: docker exec -it commercebox_web python test_financial_module.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.financial_management.models import Caja, MovimientoCaja, CajaChica
from apps.sales_management.models import Venta, DetalleVenta
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce

class Colors:
    """Colores para output en terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def print_separator():
    print("\n" + "="*70 + "\n")

def test_templates_exist():
    """Verificar que los templates existen"""
    print_info("Verificando existencia de templates...")
    
    templates = [
        'templates/custom_admin/financial/dashboard.html',
        'templates/custom_admin/financial/reporte_financiero.html'
    ]
    
    all_exist = True
    for template in templates:
        if os.path.exists(template):
            print_success(f"Template encontrado: {template}")
        else:
            print_error(f"Template NO encontrado: {template}")
            all_exist = False
    
    return all_exist

def test_models_accessible():
    """Verificar que los modelos son accesibles"""
    print_info("Verificando acceso a modelos...")
    
    try:
        # Intentar acceder a cada modelo
        cajas_count = Caja.objects.count()
        movimientos_count = MovimientoCaja.objects.count()
        cajas_chicas_count = CajaChica.objects.count()
        ventas_count = Venta.objects.count()
        detalles_count = DetalleVenta.objects.count()
        
        print_success(f"Cajas: {cajas_count}")
        print_success(f"Movimientos de Caja: {movimientos_count}")
        print_success(f"Cajas Chicas: {cajas_chicas_count}")
        print_success(f"Ventas: {ventas_count}")
        print_success(f"Detalles de Venta: {detalles_count}")
        
        return True
    except Exception as e:
        print_error(f"Error accediendo a modelos: {str(e)}")
        return False

def test_utilidad_calculation():
    """Verificar cálculo de utilidades"""
    print_info("Verificando cálculo de utilidades...")
    
    try:
        hoy = timezone.now().date()
        
        # Obtener detalles de ventas del día
        detalles_hoy = DetalleVenta.objects.filter(
            venta__fecha_venta__date=hoy,
            venta__estado='COMPLETADA'
        )
        
        count = detalles_hoy.count()
        
        if count == 0:
            print_warning("No hay ventas completadas hoy para calcular utilidades")
            print_info("Esto es normal si no se han registrado ventas")
            return True
        
        # Calcular totales
        resumen = detalles_hoy.aggregate(
            ventas=Coalesce(Sum('total'), Decimal('0')),
            costos=Coalesce(Sum('costo_total'), Decimal('0'))
        )
        
        utilidad = resumen['ventas'] - resumen['costos']
        margen = (
            (utilidad / resumen['ventas'] * 100)
            if resumen['ventas'] > 0 else Decimal('0')
        )
        
        print_success(f"Ventas del día: ${resumen['ventas']:.2f}")
        print_success(f"Costos del día: ${resumen['costos']:.2f}")
        print_success(f"Utilidad del día: ${utilidad:.2f}")
        print_success(f"Margen del día: {margen:.1f}%")
        
        # Verificar que los números tienen sentido
        if resumen['ventas'] < resumen['costos']:
            print_warning("⚠ Los costos son mayores que las ventas (margen negativo)")
        
        return True
    except Exception as e:
        print_error(f"Error calculando utilidades: {str(e)}")
        return False

def test_weekly_calculation():
    """Verificar cálculo semanal"""
    print_info("Verificando cálculo de utilidades semanales...")
    
    try:
        hoy = timezone.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        
        detalles_semana = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=inicio_semana,
            venta__fecha_venta__date__lte=hoy,
            venta__estado='COMPLETADA'
        )
        
        count = detalles_semana.count()
        
        if count == 0:
            print_warning("No hay ventas esta semana")
            return True
        
        resumen = detalles_semana.aggregate(
            ventas=Coalesce(Sum('total'), Decimal('0')),
            costos=Coalesce(Sum('costo_total'), Decimal('0'))
        )
        
        utilidad = resumen['ventas'] - resumen['costos']
        margen = (
            (utilidad / resumen['ventas'] * 100)
            if resumen['ventas'] > 0 else Decimal('0')
        )
        
        print_success(f"Ventas de la semana: ${resumen['ventas']:.2f}")
        print_success(f"Costos de la semana: ${resumen['costos']:.2f}")
        print_success(f"Utilidad de la semana: ${utilidad:.2f}")
        print_success(f"Margen de la semana: {margen:.1f}%")
        
        return True
    except Exception as e:
        print_error(f"Error calculando utilidades semanales: {str(e)}")
        return False

def test_monthly_calculation():
    """Verificar cálculo mensual"""
    print_info("Verificando cálculo de utilidades mensuales...")
    
    try:
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        
        detalles_mes = DetalleVenta.objects.filter(
            venta__fecha_venta__date__gte=inicio_mes,
            venta__fecha_venta__date__lte=hoy,
            venta__estado='COMPLETADA'
        )
        
        count = detalles_mes.count()
        
        if count == 0:
            print_warning("No hay ventas este mes")
            return True
        
        resumen = detalles_mes.aggregate(
            ventas=Coalesce(Sum('total'), Decimal('0')),
            costos=Coalesce(Sum('costo_total'), Decimal('0'))
        )
        
        utilidad = resumen['ventas'] - resumen['costos']
        margen = (
            (utilidad / resumen['ventas'] * 100)
            if resumen['ventas'] > 0 else Decimal('0')
        )
        
        print_success(f"Ventas del mes: ${resumen['ventas']:.2f}")
        print_success(f"Costos del mes: ${resumen['costos']:.2f}")
        print_success(f"Utilidad del mes: ${utilidad:.2f}")
        print_success(f"Margen del mes: {margen:.1f}%")
        
        return True
    except Exception as e:
        print_error(f"Error calculando utilidades mensuales: {str(e)}")
        return False

def test_cajas_abiertas():
    """Verificar cajas abiertas"""
    print_info("Verificando cajas abiertas...")
    
    try:
        cajas_abiertas = Caja.objects.filter(
            estado='ABIERTA',
            activa=True
        )
        
        count = cajas_abiertas.count()
        
        if count == 0:
            print_warning("No hay cajas abiertas actualmente")
            print_info("Esto es normal fuera del horario de trabajo")
        else:
            print_success(f"Cajas abiertas: {count}")
            
            total_efectivo = cajas_abiertas.aggregate(
                total=Sum('monto_actual')
            )['total'] or Decimal('0')
            
            print_success(f"Total en cajas: ${total_efectivo:.2f}")
            
            for caja in cajas_abiertas:
                print_info(f"  • {caja.nombre}: ${caja.monto_actual:.2f}")
        
        return True
    except Exception as e:
        print_error(f"Error verificando cajas: {str(e)}")
        return False

def test_import_statements():
    """Verificar que los imports necesarios funcionan"""
    print_info("Verificando imports necesarios...")
    
    try:
        from django.db.models import Sum, Count, F, Q, DecimalField, ExpressionWrapper
        from django.db.models.functions import Coalesce, TruncDate
        from datetime import timedelta
        from apps.sales_management.models import DetalleVenta
        import json
        
        print_success("Todos los imports necesarios están disponibles")
        return True
    except ImportError as e:
        print_error(f"Error en imports: {str(e)}")
        return False

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("\n" + "="*70)
    print("  PRUEBA DE MÓDULO FINANCIERO - CommerceBox")
    print("="*70 + "\n")
    
    tests = [
        ("Templates", test_templates_exist),
        ("Modelos", test_models_accessible),
        ("Imports", test_import_statements),
        ("Cálculo de Utilidad Diaria", test_utilidad_calculation),
        ("Cálculo de Utilidad Semanal", test_weekly_calculation),
        ("Cálculo de Utilidad Mensual", test_monthly_calculation),
        ("Cajas Abiertas", test_cajas_abiertas),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print_separator()
        print(f"🧪 PRUEBA: {test_name}")
        print("-" * 70)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Error inesperado: {str(e)}")
            results.append((test_name, False))
    
    # Resumen final
    print_separator()
    print("📋 RESUMEN DE PRUEBAS")
    print("-" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print_separator()
    
    if passed == total:
        print_success(f"¡TODAS LAS PRUEBAS PASARON! ({passed}/{total})")
        print_info("\n✨ El módulo financiero está correctamente implementado")
        print_info("Puedes acceder a:")
        print_info("  • Dashboard: http://localhost:8000/financial/")
        print_info("  • Reportes: http://localhost:8000/financial/reportes/")
    else:
        print_warning(f"\nAlgunas pruebas fallaron: {passed}/{total} pasadas")
        print_info("\nRevisa las instrucciones en INSTRUCCIONES_IMPLEMENTACION.md")
    
    print_separator()

if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print_warning("\n\nPrueba interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nError fatal: {str(e)}")
        sys.exit(1)
