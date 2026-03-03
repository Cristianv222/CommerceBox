import os
import django
import sys

# Setup django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

from apps.sri.models import SRILog

logs = SRILog.objects.all().order_by('-fecha_envio')[:15]
print("{:<20} | {:<7} | {}".format("VENTA", "SUCCESS", "MESSAGE"))
print("-" * 60)
for l in logs:
    # Ensure message doesn't have newlines
    msg = (l.message or "").replace('\n', ' ').replace('\r', ' ')
    print("{:<20} | {:<7} | {}".format(l.venta.numero_venta, str(l.success), msg))
