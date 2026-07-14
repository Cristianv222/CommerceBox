import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
import django
django.setup()

from apps.sales_management.models import Venta

print("=== ULTIMAS 10 VENTAS EN LA BASE DE DATOS ===")
# Obtenemos las últimas 10 ventas ordenadas por fecha de creación o ID (para ver el orden real de inserción)
ultimas_ventas = Venta.objects.all().order_by('-fecha_venta')[:10]

for v in ultimas_ventas:
    print(f"ID: {v.id} | Numero: '{v.numero_venta}' | Factura: '{v.numero_factura}' | Estado: {v.estado} | Fecha: {v.fecha_venta}")

print("\n=== MAXIMO NUMERO DE VENTA ===")
max_venta = Venta.objects.filter(numero_venta__startswith='VNT-2026-').order_by('-numero_venta').first()
if max_venta:
    print(f"El máximo según el sistema es: '{max_venta.numero_venta}'")
else:
    print("No hay ventas VNT-2026-")

