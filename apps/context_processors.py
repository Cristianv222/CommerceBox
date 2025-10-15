# apps/context_processors.py

"""
Context processors para CommerceBox
Hace que ciertas variables estén disponibles en todos los templates
"""

from apps.system_configuration.models import ConfiguracionSistema


def system_config(request):
    """
    Agrega la configuración del sistema a todos los templates
    
    Uso en template: 
        {{ config.nombre_empresa }}
        {{ config.logo_empresa.url }}
        {{ config.iva_default }}
    """
    return {
        'config': ConfiguracionSistema.get_config()
    }