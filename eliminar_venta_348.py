import os
import sys

# Configurar el entorno de Django para poder usar los modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
import django
django.setup()

from apps.sales_management.models import Venta, Devolucion, DetalleVenta

def eliminar_venta_radical():
    numero = 'VNT-2026-00348'
    print(f"[*] Buscando venta {numero}...")
    
    venta = Venta.objects.filter(numero_venta=numero).first()
    if not venta:
        print("[!] La venta no existe o ya fue eliminada.")
        return
        
    print(f"[*] Venta encontrada. Eliminando seguros y dependencias...")
    
    # 1. Eliminar devoluciones asociadas (las que bloqueaban el borrado)
    devoluciones = Devolucion.objects.filter(venta_original=venta)
    count_dev = devoluciones.count()
    devoluciones.delete()
    print(f"[+] Se eliminaron {count_dev} devoluciones que bloqueaban la venta.")
    
    # 2. Eliminar detalles de la venta (productos en el carrito de esa venta)
    detalles = DetalleVenta.objects.filter(venta=venta)
    count_det = detalles.count()
    detalles.delete()
    print(f"[+] Se eliminaron {count_det} detalles de venta.")
    
    # 3. Eliminar la venta principal
    venta.delete()
    print(f"\n[+] ¡ÉXITO TOTAL! La venta {numero} ha sido erradicada de la base de datos.")
    print("[+] El camino está 100% libre para la secuencia.")

if __name__ == '__main__':
    eliminar_venta_radical()
