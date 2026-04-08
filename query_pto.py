import sys
import os
import django

# Add the project path to sys.path
sys.path.append('c:\\GitHub\\GitHub\\CommerceBox')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')

django.setup()

from apps.electronic_invoicing.models import PuntoEmision

for p in PuntoEmision.objects.all():
    print(f"Est: {p.establecimiento}, Pto: {p.punto_emision}, Sec: {p.ultimo_secuencial}, Act: {p.activo}")

