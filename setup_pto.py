import sys
import os
import django

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')

django.setup()

from apps.electronic_invoicing.models import PuntoEmision

pto = PuntoEmision.objects.filter(activo=True).first()

if pto:
    print(f"Desactivando PuntoEmision: {pto.establecimiento}-{pto.punto_emision} (Secuencial: {pto.ultimo_secuencial})")
    pto.activo = False
    pto.save()
    
    nuevo_pto = PuntoEmision.objects.create(
        establecimiento='001',
        punto_emision='002',
        direccion_establecimiento=pto.direccion_establecimiento,
        ultimo_secuencial=0,
        activo=True
    )
    print(f"Nuevo PuntoEmision creado como activo: {nuevo_pto.establecimiento}-{nuevo_pto.punto_emision}")
else:
    # Si por alguna razon no hay ninguno
    nuevo_pto = PuntoEmision.objects.create(
        establecimiento='001',
        punto_emision='002',
        direccion_establecimiento='Matriz',
        ultimo_secuencial=0,
        activo=True
    )
    print("Se creó uno nuevo desde cero.")
