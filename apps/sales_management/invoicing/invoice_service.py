# apps/sales_management/invoicing/invoice_service.py

from django.template.loader import render_to_string
from django.conf import settings
from decimal import Decimal
import json


class InvoiceService:
    """
    Servicio para generar facturas
    """
    
    @staticmethod
    def generar_factura_html(venta):
        """
        Genera el HTML de la factura
        
        Args:
            venta: Venta
        
        Returns:
            str: HTML de la factura
        """
        # Obtener configuración de la empresa
        empresa = {
            'nombre': getattr(settings, 'EMPRESA_NOMBRE', 'CommerceBox'),
            'ruc': getattr(settings, 'EMPRESA_RUC', '0000000000001'),
            'direccion': getattr(settings, 'EMPRESA_DIRECCION', 'Ciudad'),
            'telefono': getattr(settings, 'EMPRESA_TELEFONO', '000-0000'),
            'email': getattr(settings, 'EMPRESA_EMAIL', 'info@commercebox.com'),
        }
        
        context = {
            'empresa': empresa,
            'venta': venta,
            'detalles': venta.detalles.all().select_related(
                'producto', 'quintal', 'unidad_medida'
            ),
            'pagos': venta.pagos.all(),
        }
        
        return render_to_string('sales/factura_template.html', context)
    
    @staticmethod
    def generar_numero_factura(venta):
        """
        Genera número de factura según normativa
        
        Args:
            venta: Venta
        
        Returns:
            str: Número de factura
        """
        # Formato: 001-001-000000001
        # [Establecimiento]-[Punto Emisión]-[Secuencial]
        
        establecimiento = '001'
        punto_emision = '001'
        
        # Obtener último secuencial
        from apps.sales_management.models import Venta
        ultima_con_factura = Venta.objects.filter(
            numero_factura__startswith=f'{establecimiento}-{punto_emision}-'
        ).order_by('-numero_factura').first()
        
        if ultima_con_factura:
            try:
                ultimo_secuencial = int(ultima_con_factura.numero_factura.split('-')[-1])
                siguiente = ultimo_secuencial + 1
            except:
                siguiente = 1
        else:
            siguiente = 1
        
        return f"{establecimiento}-{punto_emision}-{siguiente:09d}"
    
    @staticmethod
    def validar_datos_facturacion(venta):
        """
        Valida que la venta tenga todos los datos necesarios para facturar
        
        Args:
            venta: Venta
        
        Returns:
            dict: {'valido': bool, 'errores': list}
        """
        errores = []
        
        # Validar cliente
        if not venta.cliente:
            errores.append("Se requiere un cliente para facturar")
        else:
            if not venta.cliente.numero_documento:
                errores.append("El cliente debe tener número de documento")
            if not venta.cliente.nombres or not venta.cliente.apellidos:
                errores.append("El cliente debe tener nombres completos")
        
        # Validar detalles
        if not venta.detalles.exists():
            errores.append("La venta no tiene detalles")
        
        # Validar montos
        if venta.total <= 0:
            errores.append("El total de la venta debe ser mayor a cero")
        
        return {
            'valido': len(errores) == 0,
            'errores': errores
        }
    
    # ESPACIO RESERVADO PARA INTEGRACIÓN DE FACTURACIÓN ELECTRÓNICA
    # ============================================================
    
    @staticmethod
    def enviar_factura_electronica(venta):
        """
        PLACEHOLDER: Envía factura al SRI o sistema de facturación electrónica
        
        Este método será implementado cuando se integre el servicio
        de facturación electrónica (ej: SRI Ecuador, SUNAT Perú, etc.)
        
        Args:
            venta: Venta a facturar
        
        Returns:
            dict: Resultado del envío
        """
        # TODO: Implementar integración con servicio de facturación
        
        return {
            'exito': False,
            'mensaje': 'Facturación electrónica no configurada',
            'clave_acceso': None,
            'xml': None,
            'pdf_url': None
        }
    
    @staticmethod
    def consultar_estado_factura(clave_acceso):
        """
        PLACEHOLDER: Consulta estado de factura en el SRI
        
        Args:
            clave_acceso: Clave de acceso de la factura
        
        Returns:
            dict: Estado de la factura
        """
        # TODO: Implementar consulta al SRI
        
        return {
            'estado': 'PENDIENTE',
            'mensaje': 'Consulta no disponible'
        }