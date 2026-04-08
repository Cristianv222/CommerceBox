import sys
import os
import django

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

from apps.electronic_invoicing.models import ComprobanteElectronico
from apps.electronic_invoicing.tasks import procesar_factura_electronica

comprobante_id = '2d859579-6bce-4e7b-9443-237b43c026a3'
comprobante = ComprobanteElectronico.objects.get(pk=comprobante_id)

print(f"Reseteando comprobante {comprobante_id}")
comprobante.estado = 'CREADO'
comprobante.clave_acceso = None
comprobante.xml_generado = None
comprobante.xml_firmado = None
comprobante.xml_autorizado = None
comprobante.mensajes_error = None
comprobante.save()

print("Enviando tarea a Celery...")
procesar_factura_electronica.delay(comprobante_id)
print("Tarea enviada!")
