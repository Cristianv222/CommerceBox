import os
import sys

# Configurar el entorno de Django para poder usar los modelos en el script
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
import django
django.setup()

from apps.sales_management.models import Venta
from apps.authentication.models import Usuario

def arreglar_secuencia(numero_problema):
    print(f"[*] Verificando la venta: {numero_problema}")
    
    # 1. Verificar si ya existe en la base de datos de producción
    if Venta.objects.filter(numero_venta=numero_problema).exists():
        venta = Venta.objects.get(numero_venta=numero_problema)
        print(f"[!] ATENCION: La venta {numero_problema} YA EXISTE en la base de datos (Estado: {venta.estado}).")
        print("[!] Si el sistema dice que ya existe, pero no la ves, puede ser un error visual o de caché en el navegador.")
        print("[!] Solución: Pide al cajero que haga clic en 'Limpiar Carrito' y presione F5.")
        return

    # 2. Si NO existe (fue eliminada físicamente), la creamos como ANULADA para ocupar el hueco
    print(f"[-] La venta {numero_problema} NO existe físicamente. Se procedera a inyectar un registro dummy.")
    
    vendedor = Usuario.objects.filter(is_active=True).first()
    if not vendedor:
        print("[X] Error: No se encontro ningun usuario activo para asociar la venta.")
        return

    try:
        nueva_venta = Venta(
            numero_venta=numero_problema,
            vendedor=vendedor,
            estado='ANULADA',
            total=0.00,
            observaciones='Venta dummy inyectada por script para arreglar salto de secuencia.'
        )
        # Al ya tener el numero_venta seteado, el método save() del modelo Venta lo respetará
        nueva_venta.save()
        print(f"[+] EXITO: Se inyecto correctamente la venta {numero_problema} como ANULADA.")
        print("[+] Ya puedes regresar al POS y procesar la siguiente venta con normalidad.")
    except Exception as e:
        print(f"[X] Ocurrio un error al intentar inyectar la venta: {e}")

if __name__ == '__main__':
    # CAMBIAR AQUÍ EL NÚMERO QUE ESTÉ BLOQUEANDO EL SISTEMA
    # En base a tu captura, el número es 'VNT-2026-00348'
    NUMERO_BLOQUEADO = 'VNT-2026-00348'
    arreglar_secuencia(NUMERO_BLOQUEADO)
