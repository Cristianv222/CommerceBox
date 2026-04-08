import sys
import os
import django

sys.path.append('c:\\GitHub\\GitHub\\CommerceBox')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')

django.setup()

from apps.electronic_invoicing.models import ComprobanteElectronico

for c in ComprobanteElectronico.objects.order_by('-fecha_registro')[:5]:
    print(f'Estado: {c.estado}, Error: {c.mensajes_error}')
