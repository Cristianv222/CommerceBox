import sys
import os
import django

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')

django.setup()

from apps.electronic_invoicing.models import SRIConfig
cfg = SRIConfig.objects.first()

if cfg:
    print(f"Ambiente actual: {cfg.ambiente} ({cfg.get_ambiente_display()})")
    # cfg.ambiente = 1
    # cfg.save()
    # print("Ambiente cambiado a Pruebas (1) para validacion")
else:
    print("No hay configuracion.")
