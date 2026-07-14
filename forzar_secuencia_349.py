import os
import sys

# Configurar el entorno de Django para poder usar los modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
import django
django.setup()

from apps.sales_management.models import Venta
from django.utils import timezone

def forzar_secuencia():
    print("==========================================")
    print("🚀 SCRIPT PARA FORZAR LA SECUENCIA DEL POS")
    print("==========================================")
    
    año = timezone.now().year
    
    # 1. Obtener la venta máxima actual
    ultimo = Venta.objects.filter(
        numero_venta__startswith=f'VNT-{año}-'
    ).order_by('-numero_venta').first()
    
    if ultimo:
        try:
            ultimo_num = int(ultimo.numero_venta.split('-')[-1])
        except ValueError:
            ultimo_num = 1
    else:
        ultimo_num = 0
        
    print(f"[*] El último número de venta detectado es: {ultimo_num}")
    
    # 2. Si el sistema ya está en 348 (o superior), no hay que hacer nada.
    if ultimo_num >= 348:
        print(f"\n[+] ¡ÉXITO! El sistema ya superó el conflicto.")
        print(f"[+] La base de datos está registrada en {ultimo_num}.")
        print(f"[+] LA PRÓXIMA VENTA QUE HAGAS SERÁ AUTOMÁTICAMENTE LA {ultimo_num + 1}.")
        print("\n✅ INSTRUCCIONES FINALES:")
        print("1. Ve al Punto de Venta.")
        print("2. Haz clic en el botón rojo 'Limpiar Carrito'.")
        print("3. Presiona F5 en tu teclado para refrescar.")
        print("4. Empieza a facturar con normalidad (el sistema usará la 349).")
        return
        
    # 3. Si por alguna razón el sistema se quedó atascado en 347, insertamos la 348 fantasma.
    print(f"\n[*] Forzando al sistema a saltar la 348...")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        usuario_admin = User.objects.filter(is_active=True).first()
        
        if not usuario_admin:
            print("[!] Error: No se encontró ningún usuario administrador para forzar el registro.")
            return
            
        # Crear la venta 348 fantasma anulada
        nueva_venta_numero = f'VNT-{año}-00348'
        
        venta_fantasma = Venta.objects.create(
            numero_venta=nueva_venta_numero,
            vendedor=usuario_admin,
            estado='ANULADA',
            tipo_venta='CONTADO',
            total=0,
            observaciones="REGISTRO FANTASMA PARA FORZAR EL SALTO A LA VENTA 349"
        )
        print(f"\n[+] ¡ÉXITO! Se ha inyectado el registro {nueva_venta_numero} (ANULADA).")
        print(f"[+] LA PRÓXIMA VENTA QUE HAGAS SERÁ LA 349.")
        
    except Exception as e:
        print(f"\n[!] Ocurrió un error al intentar forzar el salto: {e}")

if __name__ == '__main__':
    forzar_secuencia()
