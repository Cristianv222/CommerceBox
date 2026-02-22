from apps.sri.models import SRILog
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

print("LAST SRI LOGS:")
for log in SRILog.objects.all().order_by('-fecha_envio')[:10]:
    print(f"Date: {log.fecha_envio}")
    print(f"Venta: {log.venta.numero_venta}")
    print(f"Success: {log.success}")
    print(f"Message: {log.message}")
    print(f"Status Code: {log.status_code}")
    print("-" * 20)
