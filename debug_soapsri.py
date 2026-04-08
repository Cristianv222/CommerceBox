import sys, os, django
sys.path.append('c:\\GitHub\\GitHub\\CommerceBox')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

from zeep import Client
from apps.electronic_invoicing.models import ComprobanteElectronico, SRIConfig

c = ComprobanteElectronico.objects.get(pk='c39d29c0-6d66-4881-ad0f-d526340bd6b0')
cfg = SRIConfig.objects.first()

url_recepcion = cfg.wsdl_recepcion_pruebas if cfg.ambiente == 1 else cfg.wsdl_recepcion_produccion
client = Client(url_recepcion)

# Solo para ver qué devolvió el SRI nativamente...
xml_bytes = c.xml_firmado.encode('utf-8')
try:
    res = client.service.validarComprobante(xml_bytes)
    print('=== ESTADO ===', res.estado)
    if res.comprobantes: 
        print('=== COMPROBANTES ===', str(res.comprobantes))
except Exception as e:
    print('ERROR:', e)
